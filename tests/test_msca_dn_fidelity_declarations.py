"""R01 — the fidelity register's declared half survives regeneration.

Acceptance, from ``plans/pe08_review_and_pe09_handoff_tickets.md`` R01:

* Both authoring tools retain valid operator declarations across repeated
  regeneration, and ``--check`` succeeds immediately afterwards.
* Historical and revised declarations stay distinct: a revision's declarations
  are never carried into another revision's register.
* Malformed declaration input fails without overwriting the register.
* With no declaration supplied, the register's bytes are the committed ones
  (covered by the byte-equal replay tests of the two tool suites).
* A declaration the input would not bring back — the whole half when no input
  exists, or one sub-section an existing input is silent about — is refused
  rather than silently overwritten.

The loader tests run on a temporary repository root; the two rendering tests
run against the real registers with the declaration directory redirected to a
temporary one, so no test ever writes a declaration into the production tree.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from runner.atomic_write import canonical_json_bytes
from runner.paths import find_repo_root
from tools import author_msca_dn_workspace as ws
from tools import fidelity_declarations as fd
from tools.import_external_proposal import REVISION_ORIGINAL, REVISION_RESOLVED_FIXES

REPO = find_repo_root()

def _inventory(revision: Any = REVISION_RESOLVED_FIXES) -> tuple[str, ...]:
    """The derived inventory of *revision*, read from its committed register.

    Not typed here: a sub-section added to the import must not leave these
    tests asserting against a stale list.
    """
    data = json.loads((REPO / revision.register_rel).read_text(encoding="utf-8"))
    return tuple(row["sub_section_id"] for row in data["derived"]["sub_sections"])


#: The derived inventory of both revisions, in its rendered order.
INVENTORY = _inventory()


def _row(sub_section_id: str, **extra: Any) -> dict[str, Any]:
    """One well-formed operator declaration row."""
    row: dict[str, Any] = {
        "sub_section_id": sub_section_id,
        "presence": {"value": "present", "basis": "read in the sanitised copy"},
        "transformation": {"value": "identifiers generalised", "basis": "operator reading"},
    }
    row.update(extra)
    return row


def _file(repo_root: Path, revision_id: str, payload: Any) -> Path:
    """Write *payload* as *revision_id*'s declaration input under *repo_root*."""
    target = repo_root / fd.declarations_rel(revision_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        target.write_text(payload, encoding="utf-8")
    else:
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def _payload(revision_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "record_type": fd.DECLARATIONS_RECORD_TYPE,
        "revision_id": revision_id,
        "sub_sections": rows,
    }


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


class TestWhereTheInputLives:
    def test_the_directory_sits_beside_the_registers(self) -> None:
        # fidelity_declarations cannot import the workspace tool (cycle), so the
        # one path it types is checked against that tool's own constant here.
        assert fd.DECLARATIONS_DIR_REL.parent == ws.SOURCE_DIR_REL
        for revision in (REVISION_ORIGINAL, REVISION_RESOLVED_FIXES):
            assert fd.declarations_rel(revision.revision_id).parent == fd.DECLARATIONS_DIR_REL
            assert revision.register_rel.parent == ws.SOURCE_DIR_REL


class TestLoadingADeclarationInput:
    def test_an_absent_input_is_the_empty_declaration_and_not_an_error(self, tmp_path: Path) -> None:
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        assert decls.supplied is False
        assert decls.rows == ()
        assert decls.path_rel is None and decls.sha256 is None

    def test_a_present_but_empty_table_is_a_valid_supplied_declaration(self, tmp_path: Path) -> None:
        _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", []))
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        assert decls.supplied is True and decls.rows == ()

    def test_rows_are_carried_through_unchanged_with_every_operator_field(self, tmp_path: Path) -> None:
        row = _row("2.1", evidence="p. 14", declared_by="operator", declared_status="Assumed")
        path = _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [row]))
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        assert decls.rows == (row,)
        assert decls.path_rel == fd.declarations_rel("resolved_fixes").as_posix()
        assert decls.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()

    @pytest.mark.parametrize(
        "payload, expected",
        [
            ("{not json", "is not valid JSON"),
            ([], "must hold a JSON object"),
            ({"record_type": "something_else", "revision_id": "resolved_fixes", "sub_sections": []},
             "record_type"),
            ({"record_type": fd.DECLARATIONS_RECORD_TYPE, "sub_sections": []}, "revision_id"),
            ({"record_type": fd.DECLARATIONS_RECORD_TYPE, "revision_id": "resolved_fixes"},
             "sub_sections"),
            ({"record_type": fd.DECLARATIONS_RECORD_TYPE, "revision_id": "resolved_fixes",
              "sub_sections": {}}, "sub_sections"),
        ],
    )
    def test_a_malformed_file_is_refused_by_name(
        self, tmp_path: Path, payload: Any, expected: str
    ) -> None:
        _file(tmp_path, "resolved_fixes", payload)
        with pytest.raises(fd.FidelityDeclarationsError) as exc:
            fd.load_declarations(tmp_path, "resolved_fixes")
        assert expected in str(exc.value)
        assert fd.declarations_rel("resolved_fixes").name in str(exc.value)

    def test_an_input_filed_under_the_wrong_revision_is_refused(self, tmp_path: Path) -> None:
        # Decl. 4 of R01: declarations are revision-specific. A file whose body
        # names another revision is a filing error, not a declaration to carry.
        _file(tmp_path, "resolved_fixes", _payload("sanitised_v1", [_row("2.1")]))
        with pytest.raises(fd.FidelityDeclarationsError) as exc:
            fd.load_declarations(tmp_path, "resolved_fixes")
        assert "sanitised_v1" in str(exc.value) and "resolved_fixes" in str(exc.value)

    @pytest.mark.parametrize(
        "row, expected",
        [
            ("not an object", "must be a JSON object"),
            ({"presence": {"v": 1}, "transformation": {"v": 1}}, "sub_section_id"),
            ({"sub_section_id": "  ", "presence": {"v": 1}, "transformation": {"v": 1}},
             "sub_section_id"),
            ({"sub_section_id": "2.1", "transformation": {"v": 1}}, "presence"),
            ({"sub_section_id": "2.1", "presence": {"v": 1}}, "transformation"),
            ({"sub_section_id": "2.1", "presence": {}, "transformation": {"v": 1}}, "presence"),
            ({"sub_section_id": "2.1", "presence": {"v": 1}, "transformation": ""},
             "transformation"),
            ({"sub_section_id": "2.1", "presence": None, "transformation": {"v": 1}}, "presence"),
        ],
    )
    def test_a_malformed_row_is_refused_by_index_and_field(
        self, tmp_path: Path, row: Any, expected: str
    ) -> None:
        _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [_row("1.1"), row]))
        with pytest.raises(fd.FidelityDeclarationsError) as exc:
            fd.load_declarations(tmp_path, "resolved_fixes")
        assert expected in str(exc.value)
        assert "sub_sections[1]" in str(exc.value)

    def test_a_plain_string_states_a_field_as_well_as_an_object(self, tmp_path: Path) -> None:
        row = {"sub_section_id": "4", "presence": "present", "transformation": "rephrased"}
        _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [row]))
        assert fd.load_declarations(tmp_path, "resolved_fixes").rows == (row,)

    def test_a_duplicate_sub_section_is_refused(self, tmp_path: Path) -> None:
        _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [_row("2.1"), _row("2.1")]))
        with pytest.raises(fd.FidelityDeclarationsError) as exc:
            fd.load_declarations(tmp_path, "resolved_fixes")
        assert "declared twice" in str(exc.value) and "'2.1'" in str(exc.value)


# --------------------------------------------------------------------------- #
# Resolving against the derived inventory
# --------------------------------------------------------------------------- #


class TestResolvingAgainstTheDerivedInventory:
    def test_rows_are_ordered_by_the_inventory_not_by_the_file(self, tmp_path: Path) -> None:
        _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [_row("8"), _row("1.1"), _row("3.2")]))
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        rows = fd.resolve_rows(decls, INVENTORY)
        assert [r["sub_section_id"] for r in rows] == ["1.1", "3.2", "8"]

    def test_a_partial_declaration_is_allowed(self, tmp_path: Path) -> None:
        # R01 retains what the operator has declared so far; completeness is R04's.
        _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [_row("2.1")]))
        rows = fd.resolve_rows(fd.load_declarations(tmp_path, "resolved_fixes"), INVENTORY)
        assert len(rows) == 1

    def test_a_sub_section_the_revision_does_not_have_is_refused(self, tmp_path: Path) -> None:
        _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [_row("9.9")]))
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        with pytest.raises(fd.FidelityDeclarationsError) as exc:
            fd.resolve_rows(decls, INVENTORY)
        assert "'9.9'" in str(exc.value) and "derived inventory" in str(exc.value)

    def test_the_input_block_names_the_input_and_its_bytes(self, tmp_path: Path) -> None:
        _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [_row("2.1")]))
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        block = fd.input_block(decls, fd.resolve_rows(decls, INVENTORY))
        assert block["path"] == decls.path_rel
        assert block["sha256"] == decls.sha256
        assert block["revision_id"] == "resolved_fixes"
        assert block["declared_sub_sections"] == 1

    def test_no_input_block_is_rendered_when_nothing_was_supplied(self, tmp_path: Path) -> None:
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        assert fd.input_block(decls, ()) is None


# --------------------------------------------------------------------------- #
# The guard against silent loss
# --------------------------------------------------------------------------- #


class TestTheGuardAgainstSilentLoss:
    def _register(
        self, tmp_path: Path, rows: list[dict[str, Any]], input_sha256: Any = None
    ) -> Path:
        """A register holding *rows*, optionally recording the input it came from."""
        half: dict[str, Any] = {"sub_sections": rows}
        if input_sha256 is not None:
            half["declaration_input"] = {"sha256": input_sha256}
        target = tmp_path / REVISION_RESOLVED_FIXES.register_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical_json_bytes({"declared": half}))
        return target

    def test_declarations_typed_into_the_register_with_no_input_are_refused(
        self, tmp_path: Path
    ) -> None:
        self._register(tmp_path, [_row("2.1")])
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        with pytest.raises(fd.FidelityDeclarationsError) as exc:
            fd.guard_against_silent_loss(tmp_path, REVISION_RESOLVED_FIXES.register_rel, decls)
        message = str(exc.value)
        assert REVISION_RESOLVED_FIXES.register_rel.as_posix() in message
        assert fd.declarations_rel("resolved_fixes").as_posix() in message

    def test_an_empty_declared_half_passes_the_guard(self, tmp_path: Path) -> None:
        self._register(tmp_path, [])
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        fd.guard_against_silent_loss(tmp_path, REVISION_RESOLVED_FIXES.register_rel, decls)

    def test_an_absent_register_passes_the_guard(self, tmp_path: Path) -> None:
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        fd.guard_against_silent_loss(tmp_path, REVISION_RESOLVED_FIXES.register_rel, decls)

    def test_a_declaration_the_input_restates_may_differ_freely(self, tmp_path: Path) -> None:
        # The input owns a sub-section it declares, so the register's copy of it
        # is merely stale: --check reports it and a write refreshes it.
        self._register(tmp_path, [_row("2.1", evidence="the register's older wording")])
        _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [_row("2.1")]))
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        fd.guard_against_silent_loss(tmp_path, REVISION_RESOLVED_FIXES.register_rel, decls)

    def test_a_row_typed_in_beside_the_input_it_was_rendered_from_is_refused(
        self, tmp_path: Path
    ) -> None:
        # The gap the whole-file guard missed: an input exists, so the register
        # looked merely stale, and the row the operator typed into it would
        # have vanished on the next write. The recorded sha256 is the input's
        # own, so the register was rendered from exactly this input.
        path = _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [_row("2.1")]))
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        self._register(tmp_path, [_row("2.1"), _row("3.2")], input_sha256=sha)
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        with pytest.raises(fd.FidelityDeclarationsError) as exc:
            fd.guard_against_silent_loss(tmp_path, REVISION_RESOLVED_FIXES.register_rel, decls)
        message = str(exc.value)
        assert "3.2" in message and "2.1" not in message
        assert fd.declarations_rel("resolved_fixes").as_posix() in message
        assert "To withdraw a declaration" in message

    def test_a_withdrawal_through_the_input_is_allowed(self, tmp_path: Path) -> None:
        # The register records the input bytes it was rendered from. A different
        # sha256 means the operator has since edited the input, so the row it no
        # longer declares was withdrawn, not lost.
        _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [_row("2.1")]))
        self._register(
            tmp_path, [_row("2.1"), _row("3.2")], input_sha256="0" * 64
        )
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        fd.guard_against_silent_loss(tmp_path, REVISION_RESOLVED_FIXES.register_rel, decls)

    def test_a_register_that_records_no_input_is_refused_for_its_own_rows(
        self, tmp_path: Path
    ) -> None:
        # Rows with no recorded input were typed in: nothing rendered them.
        _file(tmp_path, "resolved_fixes", _payload("resolved_fixes", [_row("2.1")]))
        self._register(tmp_path, [_row("2.1"), _row("3.2")])
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        with pytest.raises(fd.FidelityDeclarationsError) as exc:
            fd.guard_against_silent_loss(tmp_path, REVISION_RESOLVED_FIXES.register_rel, decls)
        assert "3.2" in str(exc.value)

    def test_deleting_the_input_never_counts_as_a_withdrawal(self, tmp_path: Path) -> None:
        # A deleted input cannot be told from a lost one, so the whole-file case
        # is refused even when the register records an input.
        self._register(tmp_path, [_row("2.1")], input_sha256="0" * 64)
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        with pytest.raises(fd.FidelityDeclarationsError) as exc:
            fd.guard_against_silent_loss(tmp_path, REVISION_RESOLVED_FIXES.register_rel, decls)
        assert "no declaration input stands behind them" in str(exc.value)

    def test_the_whole_file_case_names_every_orphaned_sub_section(self, tmp_path: Path) -> None:
        self._register(tmp_path, [_row("2.1"), _row("3.2")])
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        with pytest.raises(fd.FidelityDeclarationsError) as exc:
            fd.guard_against_silent_loss(tmp_path, REVISION_RESOLVED_FIXES.register_rel, decls)
        assert "2.1, 3.2" in str(exc.value)
        assert "no declaration input stands behind them" in str(exc.value)

    def test_validate_inputs_guards_every_revision_it_is_given(self, tmp_path: Path) -> None:
        self._register(tmp_path, [_row("2.1")])
        pairs = [
            (REVISION_ORIGINAL.revision_id, REVISION_ORIGINAL.register_rel),
            (REVISION_RESOLVED_FIXES.revision_id, REVISION_RESOLVED_FIXES.register_rel),
        ]
        # The first revision's register does not exist here, so only the
        # revision whose register carries an orphan is refused.
        fd.validate_inputs(tmp_path, pairs[:1])
        with pytest.raises(fd.FidelityDeclarationsError):
            fd.validate_inputs(tmp_path, pairs)

    def test_an_unreadable_register_is_refused_before_it_is_overwritten(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / REVISION_RESOLVED_FIXES.register_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{not json", encoding="utf-8")
        decls = fd.load_declarations(tmp_path, "resolved_fixes")
        with pytest.raises(fd.FidelityDeclarationsError) as exc:
            fd.guard_against_silent_loss(tmp_path, REVISION_RESOLVED_FIXES.register_rel, decls)
        assert "is not valid JSON" in str(exc.value)


# --------------------------------------------------------------------------- #
# The rendered register
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Both registers, rendered with a declaration input for one revision only.

    ``DECLARATIONS_DIR_REL`` is redirected to a temporary absolute directory:
    ``repo_root / <absolute path>`` is that absolute path, so the real
    ``docs/`` tree is never written to by this test.
    """
    directory = tmp_path_factory.mktemp("declarations")
    rows = [_row("3.2"), _row("1.1")]
    (directory / "resolved_fixes.json").write_text(
        json.dumps(_payload("resolved_fixes", rows), indent=2), encoding="utf-8"
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(fd, "DECLARATIONS_DIR_REL", directory)
        return {
            "resolved_fixes": ws.render_register(REPO, REVISION_RESOLVED_FIXES),
            "resolved_fixes_again": ws.render_register(REPO, REVISION_RESOLVED_FIXES),
            "sanitised_v1": ws.render_register(REPO, REVISION_ORIGINAL),
            "input_sha256": hashlib.sha256(
                (directory / "resolved_fixes.json").read_bytes()
            ).hexdigest(),
        }


class TestTheRenderedDeclaredHalf:
    def test_the_declarations_reach_the_register_in_inventory_order(self, rendered: dict) -> None:
        declared = rendered["resolved_fixes"]["declared"]
        assert [r["sub_section_id"] for r in declared["sub_sections"]] == ["1.1", "3.2"]
        assert declared["sub_sections"][0]["presence"]["value"] == "present"

    def test_the_register_names_the_input_it_carried(self, rendered: dict) -> None:
        block = rendered["resolved_fixes"]["declared"]["declaration_input"]
        assert block["sha256"] == rendered["input_sha256"]
        assert block["declared_sub_sections"] == 2

    def test_regeneration_is_deterministic(self, rendered: dict) -> None:
        assert canonical_json_bytes(rendered["resolved_fixes"]) == canonical_json_bytes(
            rendered["resolved_fixes_again"]
        )

    def test_the_other_revision_keeps_its_own_empty_declared_half(self, rendered: dict) -> None:
        # Criterion 2 of R01: one revision's declarations never reach another's.
        declared = rendered["sanitised_v1"]["declared"]
        assert declared["sub_sections"] == []
        assert "declaration_input" not in declared

    def test_the_committed_registers_carry_no_declaration_input_today(self) -> None:
        for revision in (REVISION_ORIGINAL, REVISION_RESOLVED_FIXES):
            declared = json.loads(
                (REPO / revision.register_rel).read_text(encoding="utf-8")
            )["declared"]
            assert declared["sub_sections"] == []
            assert "declaration_input" not in declared
            assert not (REPO / fd.declarations_rel(revision.revision_id)).exists()


# --------------------------------------------------------------------------- #
# The round trip: both tools, a temporary repository root
# --------------------------------------------------------------------------- #

#: What the two authoring tools read. Copied into a temporary root so the
#: round trip writes declarations and registers without touching the real tree.
_WORLD_TREES = (
    "docs/tier3_project_instantiation/source_materials/msca_dn",
    "docs/tier2a_instrument_schemas/application_forms/msca",
    "docs/tier2a_instrument_schemas/evaluation_forms/msca",
    "workspaces/msca_dn",
)
_WORLD_FILES = ("harness/evaluator_scorecard_msca_dn.json",)


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A temporary repository root holding only what the two tools read."""
    import shutil

    root = tmp_path_factory.mktemp("repo")
    for rel in _WORLD_TREES:
        shutil.copytree(REPO / rel, root / rel)
    for rel in _WORLD_FILES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, root / rel)
    return root


def _declare(root: Path, revision_id: str, rows: list[dict[str, Any]]) -> None:
    target = root / fd.declarations_rel(revision_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(_payload(revision_id, rows), indent=2), encoding="utf-8")


def _declared(root: Path, revision: Any) -> dict[str, Any]:
    return json.loads((root / revision.register_rel).read_text(encoding="utf-8"))["declared"]


class TestTheRoundTripThroughBothTools:
    """One scenario, in order: declare, regenerate, rebuild, tamper, refuse."""

    def test_01_the_copied_tree_replays_before_anything_is_declared(self, world: Path) -> None:
        import tools.import_external_proposal as ie

        assert ws.check(world) == []
        assert ie.check(world) == []

    def test_02_a_declaration_reaches_both_registers_and_check_passes_after(
        self, world: Path
    ) -> None:
        import tools.import_external_proposal as ie

        _declare(world, "sanitised_v1", [_row("1.2")])
        _declare(world, "resolved_fixes", [_row("3.1"), _row("2.4")])
        # The first revision's register is the workspace tool's; the revision's
        # register is the importer's. Both must carry the declarations.
        assert REVISION_ORIGINAL.register_rel.as_posix() in ws.author(world)
        assert REVISION_RESOLVED_FIXES.register_rel.as_posix() in ie.author(world)
        assert [r["sub_section_id"] for r in _declared(world, REVISION_ORIGINAL)["sub_sections"]] == ["1.2"]
        assert [
            r["sub_section_id"] for r in _declared(world, REVISION_RESOLVED_FIXES)["sub_sections"]
        ] == ["2.4", "3.1"]
        assert ws.check(world) == [] and ie.check(world) == []

    def test_03_repeated_regeneration_changes_nothing(self, world: Path) -> None:
        import tools.import_external_proposal as ie

        before = (world / REVISION_RESOLVED_FIXES.register_rel).read_bytes()
        assert ws.author(world) == [] and ie.author(world) == []
        assert (world / REVISION_RESOLVED_FIXES.register_rel).read_bytes() == before

    def test_04_a_deleted_register_is_rebuilt_with_its_declarations(self, world: Path) -> None:
        import tools.import_external_proposal as ie

        register = world / REVISION_RESOLVED_FIXES.register_rel
        before = register.read_bytes()
        register.unlink()
        assert ie.check(world) == [REVISION_RESOLVED_FIXES.register_rel.as_posix()]
        ie.author(world)
        assert register.read_bytes() == before

    def test_05_a_stale_derived_field_is_detected_and_regenerated(self, world: Path) -> None:
        import tools.import_external_proposal as ie

        register = world / REVISION_RESOLVED_FIXES.register_rel
        before = register.read_bytes()
        tampered = json.loads(register.read_text(encoding="utf-8"))
        tampered["derived"]["pages"] = 1
        register.write_bytes(canonical_json_bytes(tampered))
        assert REVISION_RESOLVED_FIXES.register_rel.as_posix() in ie.check(world)
        ie.author(world)
        assert register.read_bytes() == before

    def test_06_a_malformed_input_refuses_without_touching_the_register(self, world: Path) -> None:
        import tools.import_external_proposal as ie

        # The first revision's input, so both tools reach it: the workspace tool
        # renders that register and the importer renders both.
        register = world / REVISION_ORIGINAL.register_rel
        path = world / fd.declarations_rel("sanitised_v1")
        _declare(world, "sanitised_v1", [_row("1.2")])
        ws.author(world)
        before = register.read_bytes()
        kept = path.read_bytes()
        path.write_text('{"record_type": "fidelity_declarations"}', encoding="utf-8")
        for call in (ws.author, ws.check, ie.author, ie.check):
            with pytest.raises(fd.FidelityDeclarationsError) as exc:
                call(world)
            assert "revision_id" in str(exc.value)
        assert register.read_bytes() == before
        path.write_bytes(kept)
        assert ws.check(world) == []

    def test_07_removing_the_input_refuses_rather_than_erasing_the_register(
        self, world: Path
    ) -> None:
        import tools.import_external_proposal as ie

        register = world / REVISION_RESOLVED_FIXES.register_rel
        path = world / fd.declarations_rel("resolved_fixes")
        _declare(world, "resolved_fixes", [_row("3.1"), _row("2.4")])
        ie.author(world)
        assert _declared(world, REVISION_RESOLVED_FIXES)["sub_sections"]
        before = register.read_bytes()
        path.unlink()
        for call in (ie.author, ie.check):
            with pytest.raises(fd.FidelityDeclarationsError) as exc:
                call(world)
            assert fd.declarations_rel("resolved_fixes").as_posix() in str(exc.value)
            assert REVISION_RESOLVED_FIXES.register_rel.as_posix() in str(exc.value)
        assert register.read_bytes() == before
        _declare(world, "resolved_fixes", [_row("3.1"), _row("2.4")])
        assert ie.check(world) == []

    def test_08_a_row_typed_into_the_register_beside_an_input_is_refused(
        self, world: Path
    ) -> None:
        import tools.import_external_proposal as ie

        register = world / REVISION_RESOLVED_FIXES.register_rel
        _declare(world, "resolved_fixes", [_row("3.1")])
        ie.author(world)
        typed = json.loads(register.read_text(encoding="utf-8"))
        typed["declared"]["sub_sections"].append(_row("1.4"))
        register.write_bytes(canonical_json_bytes(typed))
        before = register.read_bytes()
        for call in (ie.author, ie.check):
            with pytest.raises(fd.FidelityDeclarationsError) as exc:
                call(world)
            assert "1.4" in str(exc.value)
        assert register.read_bytes() == before
        _declare(world, "resolved_fixes", [_row("3.1"), _row("1.4")])
        ie.author(world)
        assert [r["sub_section_id"] for r in _declared(world, REVISION_RESOLVED_FIXES)["sub_sections"]] == ["1.4", "3.1"]
        assert ie.check(world) == []
