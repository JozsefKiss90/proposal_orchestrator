"""AN7 — Table 1.4.1 synthesis (stage A4 of the anonymisation pipeline).

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN7:

1. On the fixture, the synthetic table has the same row count and layout as
   the source table.
2. Every band contains the source value it replaces.
3. Each fixture supervisor carries one pseudonym across the whole document.
4. The real-to-synthetic row map is written only to the private store.

The checks read the synthesised PDF with PyMuPDF directly and compare it with
the fixture's own constants, not with the row map the stage under test wrote.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterator

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import anonymisation_intake as ai  # noqa: E402
from runner import anonymisation_policy as ap  # noqa: E402
from runner import anonymisation_redaction as ar  # noqa: E402
from runner import anonymisation_table as at  # noqa: E402
from runner.dry_import import measure  # noqa: E402
from tests import _anonymisation_fixture as fx  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

SUPERVISORS = {0: "E01", 1: "E02", 2: "E03"}
CODES = {"E01": "S01", "E02": "S02", "E03": "S03"}
BAND_COLUMNS = (4, 5, 6, 7)
_BAND = re.compile(r"^(\d+) to (\d+)$|^(\d+) or more$|^(\d+)-(\d+)$|^(\d+)\+$")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def policy() -> ap.LoadedPolicy:
    return ap.load(ap.STARTING_POLICY_PATH)


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory, policy: ap.LoadedPolicy) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("an7")
    built = fx.build(root / "fixture")
    intake = ai.intake(pdf=built.pdf, expected_sha256=_sha(built.pdf), out_dir=root / "intake")
    private = root / "private"
    dictionary = fx.write_dictionary(private)
    redacted = ar.redact(
        pdf=built.pdf, intake_record=intake.intake_record, policy=policy,
        policy_sha256=policy.sha256, dictionary=dictionary,
        dictionary_sha256=ap.policy_sha256(fx.DICTIONARY), out_dir=root / "a2",
    )
    return {
        "root": root,
        "source": built.pdf,
        "intake_record": intake.intake_record,
        "dictionary": dictionary,
        "derivative": redacted.derivative,
        "redaction_log": redacted.edit_log,
        "spec": fx.write_table_spec(private),
    }


def _synthesise(world: dict[str, Any], policy: ap.LoadedPolicy, out: Path,
                **overrides: Any) -> at.SynthesisResult:
    kwargs: dict[str, Any] = {
        "derivative": world["derivative"],
        "redaction_log": world["redaction_log"],
        "intake_record": world["intake_record"],
        "policy": policy,
        "policy_sha256": policy.sha256,
        "dictionary": world["dictionary"],
        "dictionary_sha256": ap.policy_sha256(fx.DICTIONARY),
        "spec": world["spec"],
        "spec_sha256": ap.policy_sha256(fx.TABLE_SPEC),
        "out_dir": out,
    }
    swapped = Path(overrides.get("spec", ""))
    if "spec_sha256" not in overrides and swapped.is_file():
        kwargs["spec_sha256"] = ap.policy_sha256(json.loads(swapped.read_text(encoding="utf-8")))
    kwargs.update(overrides)
    return at.synthesise(**kwargs)


@pytest.fixture(scope="module")
def done(world: dict[str, Any], policy: ap.LoadedPolicy) -> at.SynthesisResult:
    return _synthesise(world, policy, world["root"] / "a4")


def _spec_with(world: dict[str, Any], name: str, edit: Any) -> Path:
    spec = copy.deepcopy(fx.TABLE_SPEC)
    edit(spec)
    return fx.write_table_spec(world["root"] / "specs" / name, spec)


def _table(pdf: Path) -> Any:
    doc = pymupdf.open(pdf)
    try:
        page = doc[fx.SUPERVISOR_TABLE_PAGE - 1]
        table = page.find_tables(strategy="lines_strict").tables[0]
        return {
            "bbox": tuple(round(v, 2) for v in table.bbox),
            "rows": table.row_count,
            "cols": table.col_count,
            "cells": [tuple(round(v, 2) for v in c) if c else None for c in table.cells],
            "text": table.extract(),
        }
    finally:
        doc.close()


def _text_in(pdf: Path, page: int, rect: list[float]) -> str:
    doc = pymupdf.open(pdf)
    try:
        return doc[page - 1].get_textbox(pymupdf.Rect(rect))
    finally:
        doc.close()


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


# --------------------------------------------------------------------------- #
# 1. Same row count and layout
# --------------------------------------------------------------------------- #


def test_the_synthetic_table_keeps_the_source_tables_rows_and_layout(
        world: dict[str, Any], done: at.SynthesisResult) -> None:
    source, synthetic = _table(world["source"]), _table(done.derivative)
    assert synthetic["rows"] == source["rows"] == 1 + len(fx.SUPERVISOR_ROWS)
    assert synthetic["cols"] == source["cols"] == len(fx.SUPERVISOR_TABLE_HEADER)
    assert synthetic["bbox"] == source["bbox"]
    assert synthetic["cells"] == source["cells"]
    assert synthetic["text"][0] == list(fx.SUPERVISOR_TABLE_HEADER)


def test_the_dry_import_measures_the_same_table_inventory(
        world: dict[str, Any], done: at.SynthesisResult) -> None:
    def inventory(pdf: Path) -> list[tuple[Any, ...]]:
        tables = measure(pdf)["tables"]["per_table"]
        return [(t["page"], t["index"], t["rows"], t["cols"], tuple(t["header"])) for t in tables]

    assert inventory(done.derivative) == inventory(world["source"])


def test_only_text_changes_no_drawing_or_page_is_added(
        world: dict[str, Any], done: at.SynthesisResult) -> None:
    def drawings(pdf: Path) -> list[int]:
        doc = pymupdf.open(pdf)
        try:
            return [len(page.get_drawings()) for page in doc]
        finally:
            doc.close()

    assert drawings(done.derivative) == drawings(world["derivative"])


# --------------------------------------------------------------------------- #
# 2. Every band contains the source value it replaces
# --------------------------------------------------------------------------- #


def _band(text: str) -> tuple[int, float]:
    m = _BAND.match(text.strip())
    assert m, f"{text!r} is not a band"
    groups = [g for g in m.groups()]
    if groups[0] is not None:
        return int(groups[0]), int(groups[1])
    if groups[2] is not None:
        return int(groups[2]), float("inf")
    if groups[3] is not None:
        return int(groups[3]), int(groups[4])
    return int(groups[5]), float("inf")


@pytest.mark.parametrize("row", range(len(fx.SUPERVISOR_ROWS)))
@pytest.mark.parametrize("col", BAND_COLUMNS)
def test_every_band_contains_the_source_value_it_replaces(
        done: at.SynthesisResult, row: int, col: int) -> None:
    cell = _table(done.derivative)["text"][row + 1][col]
    low, high = _band(cell)
    source = int(fx.SUPERVISOR_ROWS[row][col])
    assert low <= source <= high
    assert low < high, "a band of one value keeps the exact metric"


def test_the_categorical_columns_carry_the_specs_mapped_values(done: at.SynthesisResult) -> None:
    text = _table(done.derivative)["text"]
    maps = {c["index"]: c["map"] for c in fx.TABLE_SPEC["columns"] if c["rule"] == "map"}
    for row, source in enumerate(fx.SUPERVISOR_ROWS):
        for col, mapping in maps.items():
            assert text[row + 1][col] == mapping[source[col]]
        assert text[row + 1][2] == source[2], "degree level is kept"
        assert text[row + 1][8] == source[8], "the DN role is kept"


def test_no_exact_metric_or_source_label_survives_in_the_table(done: at.SynthesisResult) -> None:
    text = _table(done.derivative)["text"]
    for row, source in enumerate(fx.SUPERVISOR_ROWS):
        for col in (*BAND_COLUMNS, 3, 9):
            assert text[row + 1][col] != source[col]


# --------------------------------------------------------------------------- #
# 3. One pseudonym per supervisor across the whole document
# --------------------------------------------------------------------------- #


def test_each_supervisor_row_carries_the_pseudonym_a2_gave_that_supervisor(
        done: at.SynthesisResult) -> None:
    text = _table(done.derivative)["text"]
    for row, entry in SUPERVISORS.items():
        codes = set(re.findall(r"\bS\d{2}\b", text[row + 1][0]))
        assert codes == {CODES[entry]}


def test_every_occurrence_of_a_supervisor_reads_the_same_pseudonym(
        world: dict[str, Any], done: at.SynthesisResult) -> None:
    log = json.loads(world["redaction_log"].read_text(encoding="utf-8"))
    seen: dict[str, set[str]] = {entry: set() for entry in CODES}
    for edit in log["page_text"]["edits"]:
        if edit["entry_id"] in CODES and not edit["removed"]:
            found = set(re.findall(r"\bS\d{2}\b", _text_in(done.derivative, edit["page"],
                                                             edit["rect"])))
            seen[edit["entry_id"]] |= found
    assert seen == {entry: {code} for entry, code in CODES.items()}
    # E01 is named in prose on pages 1 and 2 as well as in the table, so the
    # check is not vacuous. (Page 3's reference entry is replaced as a
    # self-citation, E20, not as the person.)
    pages = {e["page"] for e in log["page_text"]["edits"] if e["entry_id"] == "E01"}
    assert pages >= {1, 2}
    assert sum(e["entry_id"] == "E01" for e in log["page_text"]["edits"]) >= 4


def test_no_supervisor_name_and_no_stray_code_remains_anywhere_in_the_document(
        done: at.SynthesisResult) -> None:
    import unicodedata

    doc = pymupdf.open(done.derivative)
    try:
        text = "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
    folded = "".join(c for c in unicodedata.normalize("NFKD", text)
                     if not unicodedata.combining(c)).casefold().replace("-\n", "")
    for family in ("vantrell", "quist", "ostrander", "orsolya", "halvard"):
        assert family not in folded
    assert set(re.findall(r"\bS\d{2}\b", text)) == set(CODES.values())


def test_the_row_map_records_each_supervisors_pseudonym_and_occurrences(
        done: at.SynthesisResult) -> None:
    row_map = json.loads(done.row_map.read_text(encoding="utf-8"))
    rows = {r["row"]: r for r in row_map["rows"]}
    for row, entry in SUPERVISORS.items():
        assert rows[row + 1]["supervisor"]["entry_id"] == entry
        assert rows[row + 1]["supervisor"]["pseudonym"] == CODES[entry]
    assert rows[1]["supervisor"]["occurrences_outside_table"] > 0


def test_pseudonym_code_reads_one_code_from_every_replacement(policy: ap.LoadedPolicy,
                                                              world: dict[str, Any]) -> None:
    from runner.anonymisation_matching import load_dictionary

    entries = {e.id: e for e in load_dictionary(world["dictionary"], policy).entries}
    assert at.pseudonym_code(entries["E01"]) == "S01"
    assert at.pseudonym_code(entries["E09"]) == "P1"


def _dictionary_with(world: dict[str, Any], name: str, edit: Any) -> Path:
    record = copy.deepcopy(fx.DICTIONARY)
    edit({e["id"]: e for e in record["entries"]})
    path = world["root"] / "dicts" / name / fx.DICTIONARY_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def test_a_supervisor_whose_replacements_disagree_on_the_code_is_refused(
        world: dict[str, Any], policy: ap.LoadedPolicy) -> None:
    from runner.anonymisation_matching import load_dictionary

    def split(entries: dict[str, Any]) -> None:
        entries["E01"]["replacements"] = ["Supervisor S01", "S04"]

    entries = {e.id: e for e in load_dictionary(_dictionary_with(world, "split", split),
                                                policy).entries}
    with pytest.raises(at.TableRefused, match="E01"):
        at.pseudonym_code(entries["E01"])


def test_two_supervisors_sharing_a_code_are_refused(world: dict[str, Any],
                                                    policy: ap.LoadedPolicy) -> None:
    from runner.anonymisation_matching import load_dictionary

    def share(entries: dict[str, Any]) -> None:
        entries["E03"]["replacements"] = ["Supervisor S01", "S01"]

    dictionary = load_dictionary(_dictionary_with(world, "share", share), policy)
    with pytest.raises(at.TableRefused, match="S01"):
        at.person_codes(dictionary)


def test_a_pseudonym_column_with_no_a2_edit_in_a_cell_is_refused(
        world: dict[str, Any], policy: ap.LoadedPolicy) -> None:
    def expertise_is_a_person(spec: dict[str, Any]) -> None:
        spec["columns"][9] = {"index": 9, "header": "Expertise", "field": "x",
                              "rule": "pseudonym", "category": "person_name"}

    spec = _spec_with(world, "no_edit", expertise_is_a_person)
    out = world["root"] / "refused_no_edit"
    with pytest.raises(at.TableRefused, match="row 1, column 9.*dictionary"):
        _synthesise(world, policy, out, spec=spec)
    assert not out.exists() or not any(out.iterdir())


# --------------------------------------------------------------------------- #
# 4. The row map is private
# --------------------------------------------------------------------------- #


def test_the_row_map_holds_the_source_values_and_the_synthetic_ones(
        done: at.SynthesisResult) -> None:
    row_map = json.loads(done.row_map.read_text(encoding="utf-8"))
    assert row_map["schema"] == at.ROW_MAP_SCHEMA
    for record in row_map["rows"]:
        source = fx.SUPERVISOR_ROWS[record["row"] - 1]
        for cell in record["cells"]:
            if cell["rule"] == "pseudonym":
                assert "source" not in cell, "A4 never reads a name: A2 replaced it"
            else:
                assert cell["source"] == source[cell["col"]]


def test_the_synthesis_log_quotes_no_table_text(done: at.SynthesisResult) -> None:
    log = json.loads(done.log.read_text(encoding="utf-8"))
    values = set(_strings(log))
    for row in fx.SUPERVISOR_ROWS:
        for cell in row:
            assert cell not in values
    mapped = {v for c in fx.TABLE_SPEC["columns"] if c["rule"] == "map" for v in c["map"].values()}
    assert not values & mapped
    blob = json.dumps(log)
    for row in fx.SUPERVISOR_ROWS:
        for cell in row:
            if len(cell) >= 5 and not cell.isdigit():
                assert cell not in blob


def test_every_output_lands_in_the_private_directory(world: dict[str, Any],
                                                     done: at.SynthesisResult) -> None:
    out = world["root"] / "a4"
    assert {p.name for p in out.iterdir()} == {at.DERIVATIVE_FILE, at.LOG_FILE, at.ROW_MAP_FILE}
    for path in (done.derivative, done.log, done.row_map):
        assert not path.resolve().is_relative_to(REPO)


@pytest.mark.parametrize("argument", ["out_dir", "spec", "derivative", "redaction_log",
                                      "dictionary", "intake_record"])
def test_a_path_inside_the_repository_is_refused(world: dict[str, Any], policy: ap.LoadedPolicy,
                                                 argument: str) -> None:
    inside = REPO / ".scratch" / "an7_must_not_exist"
    with pytest.raises(ai.IntakeRefused, match="inside this repository"):
        _synthesise(world, policy, world["root"] / "unused", **{argument: inside})
    assert not inside.exists()


# --------------------------------------------------------------------------- #
# Pins and chains
# --------------------------------------------------------------------------- #


def test_the_derivative_must_be_the_one_a2_recorded(world: dict[str, Any],
                                                   policy: ap.LoadedPolicy) -> None:
    with pytest.raises(ai.IntakeRefused, match="not the pinned file"):
        _synthesise(world, policy, world["root"] / "wrong_pdf", derivative=world["source"])


def test_the_dictionary_must_be_the_one_a2_applied(world: dict[str, Any],
                                                  policy: ap.LoadedPolicy) -> None:
    other = _dictionary_with(world, "other", lambda e: e["E18"].update(replacements=["a fund"]))
    sha = ap.policy_sha256(json.loads(other.read_text(encoding="utf-8")))
    with pytest.raises(at.TableRefused, match="A2 applied"):
        _synthesise(world, policy, world["root"] / "other_dict", dictionary=other,
                    dictionary_sha256=sha)


def test_the_intake_record_must_be_the_one_a2_read(world: dict[str, Any],
                                                  policy: ap.LoadedPolicy) -> None:
    root = world["root"] / "second_intake"
    copy_pdf = root / "fixture" / fx.PDF_NAME
    copy_pdf.parent.mkdir(parents=True)
    shutil.copyfile(world["source"], copy_pdf)
    other = ai.intake(pdf=copy_pdf, expected_sha256=_sha(copy_pdf), out_dir=root / "intake",
                      )
    record = json.loads(other.intake_record.read_text(encoding="utf-8"))
    record["purpose_note"] = "a different record"
    other.intake_record.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(at.TableRefused, match="intake record"):
        _synthesise(world, policy, root / "a4", intake_record=other.intake_record)


def test_a_malformed_redaction_log_is_refused(world: dict[str, Any],
                                              policy: ap.LoadedPolicy) -> None:
    record = json.loads(world["redaction_log"].read_text(encoding="utf-8"))
    del record["page_text"]
    bad = world["root"] / "bad_log" / "redaction_log.json"
    bad.parent.mkdir(parents=True)
    bad.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(at.TableRefused, match="lacks"):
        _synthesise(world, policy, world["root"] / "bad_log" / "a4", redaction_log=bad)


def test_the_spec_must_hash_to_its_pin(world: dict[str, Any], policy: ap.LoadedPolicy) -> None:
    with pytest.raises(at.TableRefused, match="not the pinned table specification"):
        _synthesise(world, policy, world["root"] / "bad_pin", spec_sha256="0" * 64)


def test_the_policy_must_hash_to_its_pin(world: dict[str, Any], policy: ap.LoadedPolicy) -> None:
    with pytest.raises(ap.PolicyChanged):
        _synthesise(world, policy, world["root"] / "bad_policy", policy_sha256="1" * 64)


# --------------------------------------------------------------------------- #
# The specification
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name, edit, message", [
    ("value_outside", lambda s: s["columns"][4].update(bands=[[0, 9], [10, 19]]),
     "row 1, column 4.*no band"),
    ("one_value_band", lambda s: s["columns"][6].update(bands=[[0, 4], [5, 5], [6, None]]),
     "one value"),
    ("overlap", lambda s: s["columns"][7].update(bands=[[0, 4], [4, 9]]), "overlap"),
    ("open_not_last", lambda s: s["columns"][7].update(bands=[[0, None], [5, 9]]), "open"),
    ("missing_map", lambda s: s["columns"][3]["map"].pop("Full professor"),
     "row 1, column 3.*map"),
    ("header", lambda s: s["columns"][4].update(header="Citations"), "column 4.*header"),
    ("missing_column", lambda s: s["columns"].pop(), "column 9"),
    ("two_row_keys", lambda s: s["columns"][1].update(row_key=True), "row key"),
    ("row_key_not_person", lambda s: (s["columns"][0].update(row_key=False),
                                      s["columns"][1].update(row_key=True)), "row key"),
    ("unknown_rule", lambda s: s["columns"][2].update(rule="drop"), "rule"),
    ("wrong_page", lambda s: s["table"].update(page=1), "page 1"),
])
def test_a_bad_specification_is_refused_and_nothing_is_written(
        world: dict[str, Any], policy: ap.LoadedPolicy, name: str, edit: Any,
        message: str) -> None:
    spec = _spec_with(world, name, edit)
    out = world["root"] / f"refused_{name}"
    with pytest.raises(at.TableRefused, match=message):
        _synthesise(world, policy, out, spec=spec)
    assert not out.exists() or not any(out.iterdir())


def test_a_mapped_value_too_wide_for_its_cell_is_refused(world: dict[str, Any],
                                                         policy: ap.LoadedPolicy) -> None:
    def wide(spec: dict[str, Any]) -> None:
        spec["columns"][9]["map"]["Lichen symbiosis"] = "Plant biology and symbiosis research"

    out = world["root"] / "refused_wide"
    with pytest.raises(at.TableRefused, match="row 1, column 9.*wide"):
        _synthesise(world, policy, out, spec=_spec_with(world, "wide", wide))
    assert not out.exists() or not any(out.iterdir())


def test_a_band_falls_back_to_its_short_form_when_the_long_one_does_not_fit(
        world: dict[str, Any], policy: ap.LoadedPolicy) -> None:
    def big(spec: dict[str, Any]) -> None:
        # The PhDs column is 26 pt wide: "0 to 9999" overflows it at 6 pt.
        spec["columns"][6]["bands"] = [[0, 9999], [10000, None]]

    result = _synthesise(world, policy, world["root"] / "short_band",
                         spec=_spec_with(world, "big", big))
    assert _table(result.derivative)["text"][1][6] == "0-9999"


# --------------------------------------------------------------------------- #
# Replay
# --------------------------------------------------------------------------- #


def test_the_same_inputs_give_byte_equal_outputs(world: dict[str, Any], policy: ap.LoadedPolicy,
                                                 done: at.SynthesisResult) -> None:
    again = _synthesise(world, policy, world["root"] / "a4_again")
    for a, b in ((done.derivative, again.derivative), (done.log, again.log),
                 (done.row_map, again.row_map)):
        assert a.read_bytes() == b.read_bytes()
    assert again.derivative_sha256 == _sha(again.derivative)


def test_a_rerun_into_the_same_directory_is_a_no_op(world: dict[str, Any],
                                                    policy: ap.LoadedPolicy,
                                                    done: at.SynthesisResult) -> None:
    before = {p.name: p.read_bytes() for p in (world["root"] / "a4").iterdir()}
    _synthesise(world, policy, world["root"] / "a4")
    assert {p.name: p.read_bytes() for p in (world["root"] / "a4").iterdir()} == before


def test_a_rerun_that_would_write_different_bytes_is_refused(
        world: dict[str, Any], policy: ap.LoadedPolicy, done: at.SynthesisResult) -> None:
    def other(spec: dict[str, Any]) -> None:
        spec["columns"][3]["map"]["Full professor"] = "Leading"

    with pytest.raises(at.TableRefused, match="never overwritten"):
        _synthesise(world, policy, world["root"] / "a4", spec=_spec_with(world, "other", other))


# --------------------------------------------------------------------------- #
# The stage-output edit harness
# --------------------------------------------------------------------------- #


def test_the_stage_harness_refuses_a_pdf_that_is_not_the_pinned_stage_output(
        world: dict[str, Any]) -> None:
    with pytest.raises(ai.IntakeRefused, match="not the pinned file"):
        ai.apply_stage_edits(world["source"], world["intake_record"], _sha(world["derivative"]),
                             [], world["root"] / "harness" / "out.pdf")


def test_the_stage_harness_applies_edits_to_a_pinned_stage_output(world: dict[str, Any]) -> None:
    edit = ai.SpanEdit(page=fx.SUPERVISOR_TABLE_PAGE, rect=(277.0, 190.0, 305.0, 205.0),
                       replacement="X")
    out = world["root"] / "harness" / "edited.pdf"
    log = ai.apply_stage_edits(world["derivative"], world["intake_record"],
                               _sha(world["derivative"]), [edit], out)
    assert len(log) == 1 and out.is_file()
