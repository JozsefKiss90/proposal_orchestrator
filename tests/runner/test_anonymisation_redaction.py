"""AN5 — deterministic redaction (stage A2 of the anonymisation pipeline).

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN5:

1. Every planted direct identifier in the fixture is removed or replaced,
   including those in the metadata.
2. Same input, same policy hash and same dictionary hash give byte-equal
   output.
3. The edit log contains no original text.

"Direct identifier" here means every planting of an entity whose category
the policy edits automatically, except identifying numbers. Those are bands,
and no honest band fits the box of the number it replaces, so the fixture
dictionary leaves them, and Table 1.4.1's metrics, to A3 and A4. Countries
are kept by the policy (O4). Citation markers are not identifiers.

The checks read the derivative with their own normalisation (case, diacritics,
line-break hyphens, whitespace), not with the matcher under test.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import unicodedata
from pathlib import Path
from typing import Any

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import anonymisation_intake as ai  # noqa: E402
from runner import anonymisation_matching as am  # noqa: E402
from runner import anonymisation_policy as ap  # noqa: E402
from runner import anonymisation_redaction as ar  # noqa: E402
from tests import _anonymisation_fixture as fx  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

#: Categories whose plantings are not A2's to remove (see the module docstring).
NOT_A2 = {"identifying_number", "niche_topic", "identifying_figure"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _norm(text: str) -> str:
    text = text.replace("-\n", "")
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return " ".join(text.casefold().split())


@pytest.fixture(scope="module")
def policy() -> ap.LoadedPolicy:
    return ap.load(ap.STARTING_POLICY_PATH)


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("an5")
    built = fx.build(root / "fixture")
    intake = ai.intake(pdf=built.pdf, expected_sha256=_sha(built.pdf), out_dir=root / "intake")
    return {
        "root": root,
        "pdf": built.pdf,
        "intake_record": intake.intake_record,
        "dictionary": fx.write_dictionary(root / "private"),
    }


def _redact(world: dict[str, Path], policy: ap.LoadedPolicy, out: Path,
            **overrides: Any) -> ar.RedactionResult:
    kwargs: dict[str, Any] = {
        "pdf": world["pdf"],
        "intake_record": world["intake_record"],
        "policy": policy,
        "policy_sha256": policy.sha256,
        "dictionary": world["dictionary"],
        "dictionary_sha256": ap.policy_sha256(fx.DICTIONARY),
        "out_dir": out,
    }
    # A test that swaps the dictionary pins the one it swaps in.
    swapped = Path(overrides.get("dictionary", ""))
    if "dictionary_sha256" not in overrides and swapped.is_file():
        kwargs["dictionary_sha256"] = ap.policy_sha256(
            json.loads(swapped.read_text(encoding="utf-8")))
    kwargs.update(overrides)
    return ar.redact(**kwargs)


@pytest.fixture(scope="module")
def result(world: dict[str, Path], policy: ap.LoadedPolicy) -> ar.RedactionResult:
    return _redact(world, policy, world["root"] / "out")


@pytest.fixture(scope="module")
def derivative(result: ar.RedactionResult) -> dict[str, Any]:
    doc = pymupdf.open(result.derivative)
    try:
        return {
            "pages": {n: _norm(p.get_text()) for n, p in enumerate(doc, start=1)},
            "raw_pages": {n: p.get_text() for n, p in enumerate(doc, start=1)},
            "metadata": dict(doc.metadata or {}),
            "xmp": doc.get_xml_metadata(),
            "embedded": doc.embfile_names(),
            "embedded_info": [doc.embfile_info(i) for i in range(doc.embfile_count())],
        }
    finally:
        doc.close()


@pytest.fixture(scope="module")
def log(result: ar.RedactionResult) -> dict[str, Any]:
    return json.loads(result.edit_log.read_text(encoding="utf-8"))


def _direct_plantings() -> list[tuple[str, dict[str, Any]]]:
    return [
        (entity["id"], planting)
        for entity in fx.ENTITIES
        if entity["category"] not in NOT_A2 and entity["eu_status"] is None
        for planting in entity["plantings"]
        if planting["form"] != "marker"
    ]


# --------------------------------------------------------------------------- #
# 1. Every planted direct identifier is removed or replaced
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("entity_id", "planting"),
    _direct_plantings(),
    ids=lambda v: v if isinstance(v, str) else f"{v['layer']}-{v['form']}-{v.get('page')}",
)
def test_every_direct_planting_is_gone(
    derivative: dict[str, Any], entity_id: str, planting: dict[str, Any]
) -> None:
    layer = planting["layer"]
    if layer in fx.TEXT_LAYERS:
        assert _norm(planting["text"]) not in derivative["pages"][planting["page"]]
    elif layer == "metadata":
        assert _norm(planting["text"]) not in _norm(derivative["metadata"][planting["field"]])
    elif layer == "xmp":
        assert derivative["xmp"] == ""
    elif layer == "embedded_file_name":
        assert all(planting["text"] not in name.casefold() for name in derivative["embedded"])
    else:  # pragma: no cover - a new layer needs a check
        pytest.fail(f"no check for layer {layer}")


def test_every_direct_surface_is_gone_from_every_page(derivative: dict[str, Any]) -> None:
    # An entry declared match_case is checked with its case: the word it
    # shares an acronym with stays (see the test below).
    match_case = {e["id"] for e in fx.DICTIONARY["entries"] if e.get("match_case")}
    for entity in fx.ENTITIES:
        if entity["category"] in NOT_A2 or entity["eu_status"] is not None:
            continue
        for number in derivative["pages"]:
            if entity["id"] in match_case:
                assert entity["surface"] not in derivative["raw_pages"][number]
            else:
                text = derivative["pages"][number]
                assert _norm(entity["surface"]) not in text, (entity["id"], number)


def test_the_metadata_is_scrubbed(derivative: dict[str, Any], log: dict[str, Any]) -> None:
    metadata = derivative["metadata"]
    assert [metadata[f] for f in ar.CLEARED_FIELDS] == ["", "", ""]
    assert metadata["title"] == "PROJ Part B"
    assert metadata["creationDate"] == fx.PINNED_DATE
    assert derivative["xmp"] == "" and log["xmp"] == "removed"
    assert derivative["embedded"] == ["embedded_file_1.txt"]
    assert derivative["embedded_info"][0]["description"] == ""
    assert {f["field"]: f["action"] for f in log["information_fields"]} == {
        "author": "cleared", "creator": "cleared", "producer": "cleared",
        "title": "redacted", "subject": "redacted", "keywords": "unchanged",
    }


def test_what_the_policy_keeps_survives(derivative: dict[str, Any], log: dict[str, Any]) -> None:
    page1, page2, page3 = (derivative["pages"][n] for n in (1, 2, 3))
    for country in ("finland", "austria", "norway"):
        assert country in page1
    assert {k["entry_id"] for k in log["kept"]} == {"E14", "E15", "E31"}
    # The niche topic is flagged for A3 and A5, never edited.
    assert "cryo-electron tomography of lichen photobionts in high-altitude permafrost" in page1
    assert [f["entry_id"] for f in log["page_text"]["flags"]] == ["E23"]
    # Text beside an edit is untouched, and a word that shares an acronym stays.
    assert "chairs the supervisory board of" in page1
    assert "lichen varnish at altitude" in page3
    assert "h-index 37" in page2
    assert "supervisor beneficiary degree career stage h-index" in page2


def test_a_name_split_across_lines_takes_its_replacement_on_the_first_line(
    derivative: dict[str, Any], log: dict[str, Any]
) -> None:
    split = [e for e in log["page_text"]["edits"] if e["pieces"] == 2]
    assert {(e["entry_id"], e["piece"], e["removed"]) for e in split} == {
        ("E01", 0, False), ("E01", 1, True), ("E07", 0, False), ("E07", 1, True),
    }
    assert "supervisor s01" in derivative["pages"][1]


def test_a_narrow_box_takes_the_shorter_replacement(log: dict[str, Any]) -> None:
    table = [e for e in log["page_text"]["edits"] if e["page"] == 2 and e["point_size"] == 6.0]
    assert {(e["entry_id"], e["replacement_index"]) for e in table} == {
        ("E01", 1), ("E02", 1), ("E03", 1), ("E07", 1), ("E09", 1),
    }


# --------------------------------------------------------------------------- #
# 2. Byte-equal replay
# --------------------------------------------------------------------------- #


def test_replay_is_byte_equal(
    world: dict[str, Path], policy: ap.LoadedPolicy, result: ar.RedactionResult, tmp_path: Path
) -> None:
    again = _redact(world, policy, tmp_path / "replay")
    assert again.derivative.read_bytes() == result.derivative.read_bytes()
    assert again.edit_log.read_bytes() == result.edit_log.read_bytes()


def test_the_log_binds_input_policy_dictionary_and_output(
    world: dict[str, Path], policy: ap.LoadedPolicy, result: ar.RedactionResult,
    log: dict[str, Any],
) -> None:
    assert log["schema"] == ar.SCHEMA
    assert log["input"]["sha256"] == _sha(world["pdf"])
    assert log["input"]["intake_record_sha256"] == _sha(world["intake_record"])
    assert log["policy_sha256"] == policy.sha256
    assert log["dictionary_sha256"] == ap.policy_sha256(fx.DICTIONARY)
    assert log["output"]["sha256"] == _sha(result.derivative) == result.derivative_sha256


def test_a_rerun_into_the_same_directory_is_a_no_op(
    world: dict[str, Path], policy: ap.LoadedPolicy, result: ar.RedactionResult
) -> None:
    before = result.derivative.stat().st_mtime_ns
    _redact(world, policy, result.derivative.parent)
    assert result.derivative.stat().st_mtime_ns == before


def test_a_different_dictionary_is_refused_over_a_written_derivative(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    _redact(world, policy, out)
    changed = copy.deepcopy(fx.DICTIONARY)
    changed["entries"][0]["replacements"] = ["Supervisor S09", "S09"]
    other = tmp_path / "private" / "other.json"
    other.parent.mkdir()
    other.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ar.RedactionRefused, match="never overwritten"):
        _redact(world, policy, out, dictionary=other)


def test_a_dictionary_with_another_hash_is_refused(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path
) -> None:
    with pytest.raises(ar.RedactionRefused, match="not the pinned dictionary"):
        _redact(world, policy, tmp_path / "out", dictionary_sha256="0" * 64)
    assert not (tmp_path / "out").exists()


def test_a_policy_with_another_hash_is_refused(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path
) -> None:
    with pytest.raises(ap.PolicyChanged):
        _redact(world, policy, tmp_path / "out", policy_sha256="0" * 64)
    assert not (tmp_path / "out").exists()


# --------------------------------------------------------------------------- #
# 3. The edit log contains no original text
# --------------------------------------------------------------------------- #


def _texts_that_may_not_appear() -> set[str]:
    texts: set[str] = set()
    for entity in fx.ENTITIES:
        texts.add(entity["surface"])
        texts.update(p["text"] for p in entity["plantings"] if p["text"])
    for entry in fx.DICTIONARY["entries"]:
        texts.update([entry["surface"], *entry["variants"], *entry["replacements"]])
        if entry.get("person"):
            texts.update([entry["person"]["given"], entry["person"]["family"]])
    for rule in fx.DICTIONARY["regex_classes"].values():
        texts.update(rule["replacements"])
    texts.update(v for v in fx._METADATA.values() if v and not v.startswith("D:"))
    texts.add(fx._EMBEDDED_FILE)
    # Below five characters a text is a code ("PROJ", "S01") that may coincide
    # with a key or a number; the codes are checked by the structure test.
    return {t for t in texts if len(t) >= 5}


def test_the_edit_log_contains_no_original_text(result: ar.RedactionResult) -> None:
    text = result.edit_log.read_text(encoding="utf-8").casefold()
    leaked = sorted(t for t in _texts_that_may_not_appear()
                    if t.casefold() in text or _norm(t) in text)
    assert leaked == []


def test_every_log_entry_holds_locations_and_codes_only(log: dict[str, Any]) -> None:
    allowed = {
        "category", "entry_id", "regex_class", "form", "piece", "pieces", "replacement_index",
        "removed", "edit", "page", "rect", "point_size", "font", "original_fonts",
        "budget_points", "used_points",
    }
    for entry in log["page_text"]["edits"]:
        assert set(entry) <= allowed
        assert entry["entry_id"] is None or am.ENTRY_ID.match(entry["entry_id"])
    categories = {e["category"] for e in log["page_text"]["edits"]}
    assert categories == {
        "person_name", "institution", "project_identity", "location", "facility",
        "dataset_cohort", "grant", "self_citation",
    }
    assert {e["regex_class"] for e in log["page_text"]["edits"]} >= set(fx.REGEX_CLASSES)


# --------------------------------------------------------------------------- #
# Refusals
# --------------------------------------------------------------------------- #


def test_no_replacement_that_fits_is_refused_and_nothing_written(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path
) -> None:
    changed = copy.deepcopy(fx.DICTIONARY)
    changed["entries"][0]["replacements"] = ["Supervisor S01 of the network"]
    path = tmp_path / "private" / "dictionary.json"
    path.parent.mkdir()
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ar.RedactionRefused, match="entry E01 on page") as refused:
        _redact(world, policy, tmp_path / "out", dictionary=path)
    assert "vantrell" not in str(refused.value).casefold()
    assert not (tmp_path / "out").exists()


def test_a_declared_removal_is_applied(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path
) -> None:
    changed = copy.deepcopy(fx.DICTIONARY)
    changed["entries"][0]["replacements"] = ["Supervisor S01 of the network", ""]
    path = tmp_path / "private" / "dictionary.json"
    path.parent.mkdir()
    path.write_text(json.dumps(changed), encoding="utf-8")
    done = _redact(world, policy, tmp_path / "out", dictionary=path)
    log = json.loads(done.edit_log.read_text(encoding="utf-8"))
    first = [e for e in log["page_text"]["edits"] if e["entry_id"] == "E01" and e["piece"] == 0]
    # The long replacement fits a box at a line end; everywhere else the
    # declared removal applies.
    assert {(e["replacement_index"], e["removed"]) for e in first} == {(0, False), (1, True)}


def test_an_intake_on_the_word_route_is_refused(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path
) -> None:
    record = json.loads(world["intake_record"].read_text(encoding="utf-8"))
    record["route"] = "word_source"
    other = tmp_path / "intake" / ai.INTAKE_RECORD_FILE
    other.parent.mkdir()
    other.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ai.IntakeRefused, match="route"):
        _redact(world, policy, tmp_path / "out", intake_record=other)


@pytest.mark.parametrize("argument", ["pdf", "dictionary", "out_dir"])
def test_a_path_inside_the_repository_is_refused(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path, argument: str
) -> None:
    inside = REPO / ".pytest_cache" / "an5_must_not_exist"
    target = {"pdf": inside / fx.PDF_NAME, "dictionary": inside / "d.json", "out_dir": inside}
    if argument == "pdf":
        inside.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(world["pdf"], target["pdf"])
    try:
        with pytest.raises(ai.IntakeRefused, match="inside this repository"):
            _redact(world, policy, tmp_path / "out", **{argument: target[argument]})
    finally:
        shutil.rmtree(inside, ignore_errors=True)
