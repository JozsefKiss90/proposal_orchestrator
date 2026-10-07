"""R04 — revision-specific fidelity declaration drafts.

Acceptance, from ``plans/pe08_review_and_pe09_handoff_tickets.md`` R04:

* Both revision drafts cover their actual sub-section inventories.
* ``presence`` and ``transformation`` are independent.
* Measured extraction facts do not masquerade as fidelity to the original.
* Unverified original-dependent claims remain explicitly uncertain.
* Draft declarations survive the supported generation workflow after adoption.
* Dependencies on register/manifest hashes are enumerated before adopting.

The adoption tests point the declaration directory outside the repository, so
no test writes a declaration into the production tree and no test touches a
committed register.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner.atomic_write import canonical_json_bytes
from runner.paths import find_repo_root
from tools import author_msca_dn_workspace as ws
from tools import draft_fidelity_declarations as drafts
from tools import fidelity_declarations as fd
from tools.import_external_proposal import REVISION_ORIGINAL, REVISION_RESOLVED_FIXES

REPO = find_repo_root()

#: The two revisions, oldest first, as the importer declares them.
REVISIONS = (REVISION_ORIGINAL, REVISION_RESOLVED_FIXES)

#: The four statuses of CLAUDE.md §12.2 and nothing else.
STATUSES = ("Confirmed", "Inferred", "Assumed", "Unresolved")

#: The claim-scope fields of a drafted row, and the scope each must carry.
SCOPES = {
    "presence": "extraction_fidelity_against_the_sanitised_pdf",
    "transformation": "fidelity_against_the_submitted_original",
    "revision_difference": "difference_between_the_sanitised_revisions",
    "fidelity_to_submitted_original": "fidelity_against_the_submitted_original",
}


def _register(revision: Any) -> dict[str, Any]:
    return json.loads((REPO / revision.register_rel).read_text(encoding="utf-8"))


def _inventory(revision: Any) -> tuple[str, ...]:
    """*revision*'s derived inventory, in its rendered order.

    Read from the committed register rather than typed here, so a sub-section
    added to the import does not leave these tests asserting a stale list.
    """
    return tuple(
        row["sub_section_id"] for row in _register(revision)["derived"]["sub_sections"]
    )


def _draft(revision: Any) -> dict[str, Any]:
    return drafts.render_draft(REPO, revision)


def _payload_rows(drafted: dict[str, Any], revision: Any) -> dict[str, dict[str, Any]]:
    payload = drafted[revision.revision_id][drafts.PAYLOAD_KEY]
    return {row["sub_section_id"]: row for row in payload[fd.SUB_SECTIONS_KEY]}


@pytest.fixture(scope="module")
def drafted() -> dict[str, dict[str, Any]]:
    """One rendering of both drafts, shared: the hash scan is not free."""
    return {revision.revision_id: _draft(revision) for revision in REVISIONS}


# --------------------------------------------------------------------------- #
# The seam: the payload a draft hands the operator is an adoptable input
# --------------------------------------------------------------------------- #


def _place_payload(repo_root: Path, revision: Any, payload: dict[str, Any]) -> Path:
    target = repo_root / fd.declarations_rel(revision.revision_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json_bytes(payload))
    return target


class TestTheAdoptablePayload:
    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_payload_loads_through_the_declaration_reader(self, revision, drafted, tmp_path):
        """The payload is a valid declaration input for its own revision."""
        payload = drafted[revision.revision_id][drafts.PAYLOAD_KEY]
        _place_payload(tmp_path, revision, payload)

        loaded = fd.load_declarations(tmp_path, revision.revision_id)

        assert loaded.supplied
        assert tuple(row["sub_section_id"] for row in loaded.rows) == _inventory(revision)

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_payload_resolves_against_the_real_inventory(self, revision, drafted, tmp_path):
        """Every declared identifier is one the revision's derived half lists."""
        payload = drafted[revision.revision_id][drafts.PAYLOAD_KEY]
        _place_payload(tmp_path, revision, payload)
        loaded = fd.load_declarations(tmp_path, revision.revision_id)

        rows = fd.resolve_rows(loaded, _inventory(revision))

        assert len(rows) == len(_inventory(revision))

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_payload_declares_its_own_revision(self, revision, drafted):
        payload = drafted[revision.revision_id][drafts.PAYLOAD_KEY]

        assert payload["record_type"] == fd.DECLARATIONS_RECORD_TYPE
        assert payload["revision_id"] == revision.revision_id

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_a_draft_is_not_a_declaration(self, revision, drafted):
        """A draft can never be mistaken for the input it proposes."""
        draft = drafted[revision.revision_id]

        assert draft["record_type"] == drafts.DRAFT_RECORD_TYPE
        assert draft["record_type"] != fd.DECLARATIONS_RECORD_TYPE
        assert draft["review_state"] == drafts.REVIEW_STATE
        assert draft["advisory"] is True and draft["blocking"] is False


# --------------------------------------------------------------------------- #
# Coverage of the real inventories
# --------------------------------------------------------------------------- #


class TestInventoryCoverage:
    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_every_sub_section_once_in_inventory_order(self, revision, drafted):
        payload = drafted[revision.revision_id][drafts.PAYLOAD_KEY]
        ids = [row["sub_section_id"] for row in payload[fd.SUB_SECTIONS_KEY]]

        assert ids == list(_inventory(revision))
        assert len(ids) == len(set(ids))

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_the_draft_records_the_inventory_it_covered(self, revision, drafted):
        assert tuple(drafted[revision.revision_id]["derived_inventory"]) == _inventory(revision)

    def test_the_two_drafts_are_distinct_records(self, drafted):
        """Revision-specific: neither draft restates the other's revision."""
        first, second = (drafted[r.revision_id] for r in REVISIONS)

        assert first["revision_id"] != second["revision_id"]
        assert first[drafts.PAYLOAD_KEY] != second[drafts.PAYLOAD_KEY]
        assert first["adoption"]["target"] != second["adoption"]["target"]


# --------------------------------------------------------------------------- #
# The three claims, and the four statuses
# --------------------------------------------------------------------------- #


class TestClaimsAndStatuses:
    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_presence_and_transformation_are_independent(self, revision, drafted):
        """Two fields, two bases, two claim scopes — never one judgment twice."""
        for sub, row in _payload_rows(drafted, revision).items():
            presence, transformation = row["presence"], row["transformation"]
            assert presence["basis"] != transformation["basis"], sub
            assert presence["value"] != transformation["value"], sub
            assert presence["claim_scope"] != transformation["claim_scope"], sub
            assert presence["declared_status"] != transformation["declared_status"], sub

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_every_field_names_its_claim_scope(self, revision, drafted):
        for sub, row in _payload_rows(drafted, revision).items():
            for field, scope in SCOPES.items():
                assert row[field]["claim_scope"] == scope, f"{sub}/{field}"
                assert scope in drafts.CLAIM_SCOPES, scope

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_every_status_is_one_of_the_four(self, revision, drafted):
        for sub, row in _payload_rows(drafted, revision).items():
            for field in SCOPES:
                assert row[field]["declared_status"] in STATUSES, f"{sub}/{field}"
            for part in row["transformation"]["measured_parts"]:
                assert part["declared_status"] in STATUSES, sub

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_original_fidelity_is_unresolved_everywhere(self, revision, drafted):
        """Nothing here measures the original, so nothing here resolves it."""
        for sub, row in _payload_rows(drafted, revision).items():
            field = row["fidelity_to_submitted_original"]
            assert field["declared_status"] == "Unresolved", sub
            assert "private network" in field["basis"], sub
            assert field["resolution_requires"].strip(), sub

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_presence_does_not_masquerade_as_original_fidelity(self, revision, drafted):
        """A measured extraction fact is bounded to the claim it measures."""
        for sub, row in _payload_rows(drafted, revision).items():
            presence = row["presence"]
            assert presence["declared_status"] == "Confirmed", sub
            assert "fidelity_to_submitted_original" in presence["scope_limit"], sub
            assert "not a statement about the submitted original" in presence["scope_limit"], sub

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_transformation_carries_the_weaker_status(self, revision, drafted):
        """Its measured parts are Confirmed; the field itself is not."""
        for sub, row in _payload_rows(drafted, revision).items():
            transformation = row["transformation"]
            assert transformation["declared_status"] == "Assumed", sub
            assert transformation["not_measured"].strip(), sub
            assert all(
                part["declared_status"] == "Confirmed"
                for part in transformation["measured_parts"]
            ), sub

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_no_row_claims_operator_authorship(self, revision, drafted):
        for sub, row in _payload_rows(drafted, revision).items():
            assert row["declared_by"] == drafts.ROW_DECLARED_BY, sub
            assert row["review_state"] == drafts.REVIEW_STATE, sub
            assert "pending operator confirmation" in row["declared_by"], sub


# --------------------------------------------------------------------------- #
# The measured facts are the register's, not this module's
# --------------------------------------------------------------------------- #


class TestMeasuredFacts:
    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_presence_basis_quotes_the_derived_row(self, revision, drafted):
        """Every number in a presence basis is the register's own."""
        rows = _payload_rows(drafted, revision)
        for derived in _register(revision)["derived"]["sub_sections"]:
            basis = rows[derived["sub_section_id"]]["presence"]["basis"]
            for field in ("paragraphs", "table_rows", "characters", "claims"):
                assert str(derived[field]) in basis, f"{derived['sub_section_id']}/{field}"
            for page in derived["derived_pages"] + derived["declared_pages"]:
                assert str(page) in basis, derived["sub_section_id"]

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_presence_basis_quotes_the_extraction_accounting(self, revision, drafted):
        losses = _register(revision)["derived"]["per_page_extraction_losses"]
        for sub, row in _payload_rows(drafted, revision).items():
            basis = row["presence"]["basis"]
            assert str(losses["total_accounted"]) in basis, sub
            assert str(losses["total_page_chars"]) in basis, sub

    def test_the_revision_difference_is_the_measured_one(self, drafted):
        """Only 3.1 differs between the two sanitised revisions."""
        rows = _payload_rows(drafted, REVISION_RESOLVED_FIXES)
        changed = {
            sub
            for sub, row in rows.items()
            if row["revision_difference"]["value"].startswith("changed")
        }
        before = {r["sub_section_id"]: r for r in _register(REVISION_ORIGINAL)["derived"]["sub_sections"]}
        after = {r["sub_section_id"]: r for r in _register(REVISION_RESOLVED_FIXES)["derived"]["sub_sections"]}
        measured = {
            sub
            for sub in after
            if any(before[sub][f] != after[sub][f] for f in ("paragraphs", "table_rows", "characters", "claims"))
        }

        assert changed == measured
        assert changed, "the two registers differ somewhere; the draft must say where"

    def test_the_first_revision_declares_no_predecessor(self, drafted):
        for sub, row in _payload_rows(drafted, REVISION_ORIGINAL).items():
            assert row["revision_difference"]["value"].startswith("no predecessor"), sub

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_a_spanless_claim_is_attributed_by_its_id(self, revision, drafted):
        """A claim straddling a page break belongs to the sub-section its id
        names, not to both sub-sections whose page ranges meet there."""
        rows = _payload_rows(drafted, revision)
        manifest_rel = Path(_register(revision)["derived"]["import_manifest"])
        manifest = json.loads((REPO / manifest_rel).read_text(encoding="utf-8"))
        spanless = manifest["claims"]["claims_without_span"]
        assert spanless, "the manifest records a spanless claim; the test needs one"
        for claim in spanless:
            owner = claim["claim_id"].rsplit("-c", 1)[0]
            kinds = {c["kind"] for c in rows[owner]["presence"]["caveats"]}
            assert "claims_without_a_span" in kinds, owner
            for sub, row in rows.items():
                if sub == owner:
                    continue
                details = [
                    c["detail"]
                    for c in row["presence"]["caveats"]
                    if c["kind"] == "claims_without_a_span"
                ]
                assert claim["claim_id"] not in " ".join(details), sub


# --------------------------------------------------------------------------- #
# Declarations checked against measurement (ticket R04 step 7)
# --------------------------------------------------------------------------- #


class TestDeclarationChecks:
    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_every_check_names_a_register_pointer_and_a_verdict(self, revision, drafted):
        checks = drafted[revision.revision_id]["declarations_checked"]
        assert checks
        for check in checks:
            assert check["declaration"].startswith(revision.register_rel.as_posix() + "#")
            assert check["verdict"] in drafts.VERDICTS
            assert check["measurement"].strip()

    def test_the_uniform_body_size_is_contradicted_only_where_measured(self, drafted):
        """The resolved revision carries prose below the body size; the first
        one carries only bullets, so only one draft proposes the correction."""
        verdicts = {}
        for revision in REVISIONS:
            register = _register(revision)
            body = register["derived"]["body_point_size"]
            check = next(
                c
                for c in drafted[revision.revision_id]["declarations_checked"]
                if c["declaration"].endswith("reformatting/body_point_size")
            )
            verdicts[revision.revision_id] = (
                body["other_sizes_are_bullets_and_spaces_only"],
                check["verdict"],
            )
        for revision_id, (uniform, verdict) in verdicts.items():
            assert verdict == ("holds" if uniform else "contradicted"), revision_id

    def test_a_contradicted_declaration_carries_a_proposal_not_an_edit(self, drafted):
        check = next(
            c
            for c in drafted[REVISION_RESOLVED_FIXES.revision_id]["declarations_checked"]
            if c["verdict"] == "contradicted"
        )

        assert check["proposed_correction"].strip()
        assert check["correction_status"] in STATUSES
        assert check["correction_status_basis"].strip()
        assert check["reviewer_status"] == drafts.REVIEW_STATE
        assert "9.8" in json.dumps(check["evidence"], ensure_ascii=False)

    def test_the_declared_body_size_is_still_the_registers(self):
        """Nothing here applies the correction: the register is untouched."""
        register = _register(REVISION_RESOLVED_FIXES)
        declared = register["provenance"]["transformation"]["reformatting"]["body_point_size"]

        assert declared == 12


# --------------------------------------------------------------------------- #
# ESR dependencies (ticket R04 step 8)
# --------------------------------------------------------------------------- #


class TestEsrDependencies:
    def test_the_bound_revision_carries_the_dependencies(self, drafted):
        dispositions = json.loads(
            (REPO / drafts.DISPOSITIONS_REL).read_text(encoding="utf-8")
        )
        bound = dispositions["fidelity_register"].replace("\\", "/")
        for revision in REVISIONS:
            esr = drafted[revision.revision_id]["esr_dependencies"]
            if revision.register_rel.as_posix() == bound:
                assert esr["by_sub_section"], revision.revision_id
            else:
                assert esr["by_sub_section"] == [], revision.revision_id
                assert esr["binds_register"] == bound

    def test_every_declaration_dependent_row_is_accounted_for(self, drafted):
        """A row the review recommends revisiting after a declaration is
        either attached to a sub-section or listed with a question."""
        notes_rel = drafts.active_review_notes_rel(REPO)
        notes = json.loads((REPO / notes_rel).read_text(encoding="utf-8"))
        wanted = {
            row["observation_id"]
            for row in notes["rows"]
            if row.get("recommendation") == "revisit_after_declaration"
        }
        assert wanted, "the review notes carry declaration-dependent rows"
        esr = drafted[REVISION_RESOLVED_FIXES.revision_id]["esr_dependencies"]
        attached = {
            observation["observation_id"]
            for entry in esr["by_sub_section"]
            for observation in entry["observations"]
        }
        unattached = {
            entry["observation_id"]
            for entry in esr["declaration_dependent_without_a_sub_section"]
        }

        assert wanted <= attached | unattached
        assert attached.isdisjoint(unattached)

    def test_an_unattached_row_asks_rather_than_guesses(self, drafted):
        esr = drafted[REVISION_RESOLVED_FIXES.revision_id]["esr_dependencies"]
        for entry in esr["declaration_dependent_without_a_sub_section"]:
            assert entry["operator_question"].strip()
            assert "sub_section_id" not in entry

    def test_every_attached_row_says_what_confirmation_would_change(self, drafted):
        esr = drafted[REVISION_RESOLVED_FIXES.revision_id]["esr_dependencies"]
        dispositions = json.loads(
            (REPO / drafts.DISPOSITIONS_REL).read_text(encoding="utf-8")
        )
        by_id = {row["observation_id"]: row for row in dispositions["rows"]}
        for entry in esr["by_sub_section"]:
            for observation in entry["observations"]:
                assert observation["dependency"].strip()
                assert observation["what_confirmation_would_change"].strip()
                assert observation["disposition"] == by_id[observation["observation_id"]]["disposition"]

    def test_the_active_notes_are_the_unsuperseded_ones(self):
        rel = drafts.active_review_notes_rel(REPO)
        superseded = set()
        for path in (REPO / drafts.ESR_DIR_REL).glob("review_notes_*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data.get("supersedes"), str):
                superseded.add(data["supersedes"].replace("\\", "/"))

        assert rel.as_posix() not in superseded


# --------------------------------------------------------------------------- #
# Prior operator declarations are carried, never redrafted (step 6)
# --------------------------------------------------------------------------- #


class TestPriorDeclarations:
    def test_a_prior_row_wins_over_the_draft_unchanged(self):
        prior = {
            "sub_section_id": "1.2",
            "presence": {"value": "present", "basis": "operator reading"},
            "transformation": {"value": "lightly edited", "basis": "operator reading"},
            "declared_by": "operator",
        }
        drafted_rows = [
            {"sub_section_id": "1.1", "presence": {}, "transformation": {}},
            {"sub_section_id": "1.2", "presence": {}, "transformation": {}},
        ]

        merged = drafts.merge_prior([prior], drafted_rows, ["1.1", "1.2"])

        assert merged.carried == ("1.2",)
        assert merged.drafted == ("1.1",)
        assert merged.rows[1] == prior

    def test_a_prior_row_outside_the_inventory_is_refused(self):
        prior = {"sub_section_id": "99", "presence": {}, "transformation": {}}

        with pytest.raises(drafts.DraftError, match="derived inventory does not list"):
            drafts.merge_prior([prior], [], ["1.1"])

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_both_registers_declare_nothing_today(self, revision, drafted):
        prior = drafted[revision.revision_id]["prior_declarations"]

        assert prior["declared_in_the_input"] == []
        assert prior["declared_in_the_register_today"] == []
        assert prior["carried_through_unchanged"] == []
        assert prior["input_present"] is False
        assert list(prior["drafted_here"]) == list(_inventory(revision))

    def test_prior_rows_come_from_the_input_not_the_register(self, monkeypatch, tmp_path):
        """The operator's declarations live in the durable input. A register
        rendered before the last edit to that input is stale, not a source."""
        revision = REVISION_RESOLVED_FIXES
        inventory = _inventory(revision)
        declared = {
            "sub_section_id": inventory[1],
            "presence": {"value": "present", "basis": "the operator read it"},
            "transformation": {"value": "lightly edited", "basis": "the operator read it"},
            "declared_by": "operator",
        }
        monkeypatch.setattr(fd, "DECLARATIONS_DIR_REL", tmp_path)
        fd.declarations_rel(revision.revision_id).write_bytes(
            canonical_json_bytes(
                {
                    "record_type": fd.DECLARATIONS_RECORD_TYPE,
                    "revision_id": revision.revision_id,
                    "sub_sections": [declared],
                }
            )
        )

        draft = drafts.render_draft(REPO, revision)

        prior = draft["prior_declarations"]
        assert prior["input_present"] is True
        assert prior["declared_in_the_input"] == [inventory[1]]
        assert prior["carried_through_unchanged"] == [inventory[1]]
        assert inventory[1] not in prior["drafted_here"]
        rows = {
            row["sub_section_id"]: row
            for row in draft[drafts.PAYLOAD_KEY][fd.SUB_SECTIONS_KEY]
        }
        assert rows[inventory[1]] == declared
        assert any(
            row["path"] == fd.declarations_rel(revision.revision_id).as_posix()
            for row in draft["inputs"]
        )

    def test_a_row_only_the_register_holds_is_reported_not_adopted(self, monkeypatch, tmp_path):
        """The register's declared half is a rendering, so a row only it holds
        is either a withdrawal or a row typed into the output. Either way the
        draft reports the disagreement rather than carrying it."""
        revision = REVISION_RESOLVED_FIXES
        monkeypatch.setattr(fd, "DECLARATIONS_DIR_REL", tmp_path)
        fd.declarations_rel(revision.revision_id).write_bytes(
            canonical_json_bytes(
                {
                    "record_type": fd.DECLARATIONS_RECORD_TYPE,
                    "revision_id": revision.revision_id,
                    "sub_sections": [],
                }
            )
        )
        monkeypatch.setattr(
            fd,
            "read_declared_half",
            lambda repo_root, register_rel: fd.RegisterDeclaredHalf(
                sub_section_ids=("1.1",), input_sha256=None
            ),
        )

        prior = drafts.render_draft(REPO, revision)["prior_declarations"]

        assert prior["declared_only_in_the_register"] == ["1.1"]
        assert "guard_against_silent_loss" in prior["note"]
        assert "1.1" in prior["drafted_here"]


# --------------------------------------------------------------------------- #
# Hash dependencies (acceptance 6)
# --------------------------------------------------------------------------- #


class TestHashDependencies:
    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_every_pinned_artifact_really_records_the_hash(self, revision, drafted):
        adoption = drafted[revision.revision_id]["adoption"]
        sha256 = adoption["register_sha256_before_adoption"]
        assert adoption["pinned_by_hash"], revision.revision_id
        for entry in adoption["pinned_by_hash"]:
            text = (REPO / entry["path"]).read_text(encoding="utf-8-sig")
            assert sha256 in text or sha256[:16] in text, entry["path"]

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_every_path_reference_really_names_the_register(self, revision, drafted):
        needle = revision.register_rel.as_posix()
        for path in drafted[revision.revision_id]["adoption"]["referenced_by_path"]:
            assert needle in (REPO / path).read_text(encoding="utf-8-sig"), path

    def test_the_resolved_revision_pins_the_comparison_and_the_adjudication(self, drafted):
        """The two artifacts whose replay the operator must protect."""
        pinned = {
            entry["path"]
            for entry in drafted[REVISION_RESOLVED_FIXES.revision_id]["adoption"]["pinned_by_hash"]
        }

        assert "docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0001.json" in pinned
        assert "docs/tier4_orchestration_state/msca_dn/esr/semantic_adjudications_f60ae6e0a2a1.json" in pinned

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_the_import_manifest_is_enumerated_and_unaffected(self, revision, drafted):
        """Adoption rewrites the register's declared half and nothing else, so
        the manifest's own dependents are listed to show they are none."""
        manifest = drafted[revision.revision_id]["adoption"]["import_manifest"]
        register = _register(revision)

        assert manifest["path"] == register["derived"]["import_manifest"]
        assert manifest["changed_by_adoption"] is False
        assert manifest["pinned_by_hash"] == []
        # The register's derived half names the manifest, so the register is
        # always one of the manifest's path references.
        assert revision.register_rel.as_posix() in manifest["referenced_by_path"]

    def test_the_scan_excludes_the_drafts_own_directory(self, drafted):
        """A draft records the hash itself; counting it would make the scan a
        fixed point of its own output."""
        for revision in REVISIONS:
            adoption = drafted[revision.revision_id]["adoption"]
            for entry in adoption["pinned_by_hash"]:
                assert not entry["path"].startswith(drafts.DRAFTS_DIR_REL.as_posix())
            for path in adoption["referenced_by_path"]:
                assert not path.startswith(drafts.DRAFTS_DIR_REL.as_posix())


# --------------------------------------------------------------------------- #
# Determinism, and the committed artifacts
# --------------------------------------------------------------------------- #


class TestDeterminismAndTheCommittedArtifacts:
    def test_the_committed_artifacts_are_reproducible(self):
        assert drafts.check(REPO) == []

    def test_two_renderings_agree_byte_for_byte(self):
        assert drafts.render_all(REPO) == drafts.render_all(REPO)

    def test_check_writes_nothing(self, drafted):
        before = {
            rel: (REPO / rel).read_bytes() for rel in drafts.render_all(REPO)
        }

        drafts.check(REPO)

        assert {rel: (REPO / rel).read_bytes() for rel in before} == before

    def test_the_checklist_covers_both_revisions(self):
        text = (REPO / drafts.CHECKLIST_REL).read_text(encoding="utf-8")

        for revision in REVISIONS:
            assert f"## Revision `{revision.revision_id}`" in text
            assert drafts.draft_rel(revision).as_posix() in text
            for sub in _inventory(revision):
                assert f"| `{sub}` |" in text
        assert drafts.REVIEW_STATE in text
        assert "the private network only (PE-09)" in text

    def test_emit_input_prints_the_payload_and_writes_nothing(self, capsys, drafted):
        before = {rel: (REPO / rel).read_bytes() for rel in drafts.render_all(REPO)}

        exit_code = drafts.main(["--emit-input", REVISION_RESOLVED_FIXES.revision_id])

        assert exit_code == 0
        printed = json.loads(capsys.readouterr().out)
        assert printed == drafted[REVISION_RESOLVED_FIXES.revision_id][drafts.PAYLOAD_KEY]
        assert {rel: (REPO / rel).read_bytes() for rel in before} == before
        assert not (REPO / fd.declarations_rel(REVISION_RESOLVED_FIXES.revision_id)).exists()

    def test_an_unknown_revision_is_refused(self, capsys):
        assert drafts.main(["--emit-input", "no-such-revision"]) == 1
        assert "refused:" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# Adoption: the payload survives the supported generation workflow
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def adopted(tmp_path_factory) -> dict[str, dict[str, Any]]:
    """Each revision's register, re-rendered with its draft payload adopted.

    ``DECLARATIONS_DIR_REL`` is pointed at a directory outside the repository —
    ``repo_root / rel`` yields *rel* when it is absolute — so the production
    declaration directory is never written and both committed registers stay as
    they are. One full render per revision: each re-extracts its PDF.
    """
    directory = tmp_path_factory.mktemp("declarations")
    original = fd.DECLARATIONS_DIR_REL
    out: dict[str, dict[str, Any]] = {}
    try:
        fd.DECLARATIONS_DIR_REL = directory
        for revision in REVISIONS:
            payload = _draft(revision)[drafts.PAYLOAD_KEY]
            path = fd.declarations_rel(revision.revision_id)
            path.write_bytes(canonical_json_bytes(payload))
            out[revision.revision_id] = {
                "payload": payload,
                "register": ws.render_register(REPO, revision),
            }
            path.unlink()
    finally:
        fd.DECLARATIONS_DIR_REL = original
    return out


class TestAdoption:
    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_the_rendered_register_holds_every_drafted_row_unchanged(self, revision, adopted):
        """The supported workflow carries the adopted payload into the register."""
        case = adopted[revision.revision_id]
        declared = case["register"][fd.DECLARED_HALF_KEY]

        assert declared[fd.SUB_SECTIONS_KEY] == case["payload"][fd.SUB_SECTIONS_KEY]
        assert [row["sub_section_id"] for row in declared[fd.SUB_SECTIONS_KEY]] == list(
            _inventory(revision)
        )

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_the_register_records_the_input_it_was_rendered_from(self, revision, adopted):
        block = adopted[revision.revision_id]["register"][fd.DECLARED_HALF_KEY][
            fd.INPUT_BLOCK_KEY
        ]

        assert block["revision_id"] == revision.revision_id
        assert block["declared_sub_sections"] == len(_inventory(revision))
        assert len(block["sha256"]) == 64

    @pytest.mark.parametrize("revision", REVISIONS, ids=lambda r: r.revision_id)
    def test_adoption_changes_the_register_bytes(self, revision, adopted):
        """Why the hash dependencies have to be enumerated before adopting."""
        before = (REPO / revision.register_rel).read_bytes()
        after = canonical_json_bytes(adopted[revision.revision_id]["register"])

        assert after != before
        assert (REPO / revision.register_rel).read_bytes() == before

    def test_neither_revision_reads_the_others_declarations(self, adopted):
        """Revision-specific: each register's rows are its own payload's."""
        first = adopted[REVISION_ORIGINAL.revision_id]
        second = adopted[REVISION_RESOLVED_FIXES.revision_id]

        assert (
            first["register"][fd.DECLARED_HALF_KEY][fd.SUB_SECTIONS_KEY]
            != second["register"][fd.DECLARED_HALF_KEY][fd.SUB_SECTIONS_KEY]
        )
        assert (
            first["register"][fd.DECLARED_HALF_KEY][fd.INPUT_BLOCK_KEY]["sha256"]
            != second["register"][fd.DECLARED_HALF_KEY][fd.INPUT_BLOCK_KEY]["sha256"]
        )

    def test_the_production_declaration_directory_stays_empty(self):
        """This module never writes a declaration into Tier 3."""
        directory = REPO / fd.DECLARATIONS_DIR_REL

        assert sorted(p.name for p in directory.iterdir()) == ["README.md"]
