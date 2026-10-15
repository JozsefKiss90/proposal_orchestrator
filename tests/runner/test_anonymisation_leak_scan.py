"""AN8a — deterministic leak scan (the first half of stage A5).

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN8a:

1. The scan catches every planted entity in the unredacted fixture and finds
   none in the redacted fixture.
2. A mutation run that disables one normalisation makes the scan fail on the
   redacted fixture.
3. Hits are reported by location and category, with no private text in the
   report.

"Every planted entity" means every planting the entity dictionary or a regex
class covers. Three kinds are out of a text scan's reach, and the tests say so
rather than pass over them: identifying numbers (the fixture dictionary leaves
them to A3 and A4), figures whose identity is in their pixels or line art (A6
and the model attack), and countries, which the policy keeps (O4). The
citation marker "[1, 2]" is planted as a marker, not as an identifier.

Two kinds of match are listed for review instead of failing: a niche topic,
which the policy flags for A3, and a case-folded occurrence of an entry the
operator declared ``match_case``. Tier 4 records that ruling, pending the
operator: ``msca-dn-an8a-leak-scan-verdict_2026-10-15.json``.

The mutation run weakens A2, not the scan: the redaction runs with one
normalisation switched off in its own matcher, so its self-check passes, and
the scan must catch what A2 left.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import anonymisation_intake as ai  # noqa: E402
from runner import anonymisation_leak_scan as ls  # noqa: E402
from runner import anonymisation_matching as am  # noqa: E402
from runner import anonymisation_policy as ap  # noqa: E402
from runner import anonymisation_redaction as ar  # noqa: E402
from tests import _anonymisation_fixture as fx  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

#: Categories a text scan of the fixture dictionary cannot reach (see the module docstring).
OUT_OF_REACH = {"identifying_number", "identifying_figure"}

#: Plantings that sit inside a longer entity's match. Leftmost-longest gives
#: the location to the longer entity, so the hit there carries its id.
SUBSUMED: dict[tuple[str, int, str], set[str]] = {
    ("E13", 3, "figure_text"): {"E16"},       # "Brennmark Observatory"
    ("E01", 3, "reference_list"): {"E20"},    # "Vantrell, O. and Quist, H. (2021)"
    ("E02", 3, "reference_list"): {"E20", "E32"},
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def policy() -> ap.LoadedPolicy:
    return ap.load(ap.STARTING_POLICY_PATH)


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("an8a")
    built = fx.build(root / "fixture")
    intake = ai.intake(pdf=built.pdf, expected_sha256=_sha(built.pdf), out_dir=root / "intake")
    return {
        "root": root,
        "pdf": built.pdf,
        "intake_record": intake.intake_record,
        "dictionary": fx.write_dictionary(root / "private"),
    }


def _redact(world: dict[str, Path], policy: ap.LoadedPolicy, out: Path) -> ar.RedactionResult:
    return ar.redact(
        pdf=world["pdf"],
        intake_record=world["intake_record"],
        policy=policy,
        policy_sha256=policy.sha256,
        dictionary=world["dictionary"],
        dictionary_sha256=ap.policy_sha256(fx.DICTIONARY),
        out_dir=out,
    )


def _scan(world: dict[str, Path], policy: ap.LoadedPolicy, pdf: Path, out: Path,
          **overrides: Any) -> ls.LeakScanResult:
    kwargs: dict[str, Any] = {
        "derivative": pdf,
        "policy": policy,
        "policy_sha256": policy.sha256,
        "dictionary": world["dictionary"],
        "dictionary_sha256": ap.policy_sha256(fx.DICTIONARY),
        "out_dir": out,
    }
    kwargs.update(overrides)
    return ls.leak_scan(**kwargs)


def _report(result: ls.LeakScanResult) -> dict[str, Any]:
    return json.loads(result.report.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def unredacted(world: dict[str, Path], policy: ap.LoadedPolicy) -> dict[str, Any]:
    result = _scan(world, policy, world["pdf"], world["root"] / "scan_original")
    return {"result": result, "report": _report(result)}


@pytest.fixture(scope="module")
def redacted(world: dict[str, Path], policy: ap.LoadedPolicy) -> dict[str, Any]:
    derivative = _redact(world, policy, world["root"] / "redacted").derivative
    result = _scan(world, policy, derivative, world["root"] / "scan_redacted")
    return {"pdf": derivative, "result": result, "report": _report(result)}


def _scanned_plantings() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [
        (entity, planting)
        for entity in fx.ENTITIES
        if entity["category"] not in OUT_OF_REACH and entity["eu_status"] is None
        for planting in entity["plantings"]
        if planting["form"] != "marker"
    ]


def _in_band(hit: dict[str, Any], page: int, layer: str) -> bool:
    low, high = fx.LAYER_BANDS[(page, layer)]
    return hit["page"] == page and any(low <= (r[1] + r[3]) / 2 <= high for r in hit["rects"])


def _owner(hit: dict[str, Any], entity: dict[str, Any], accepted: set[str]) -> bool:
    if entity["regex_class"] is not None:
        return hit["regex_class"] == entity["regex_class"]
    return hit["entry_id"] in accepted


# --------------------------------------------------------------------------- #
# 1. Every planted entity is caught; the redacted fixture is clean
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("entity", "planting"),
    _scanned_plantings(),
    ids=lambda v: v["id"] if "plantings" in v else f"{v['layer']}-{v['form']}-{v.get('page')}",
)
def test_every_planting_is_caught_where_it_was_planted(
    unredacted: dict[str, Any], entity: dict[str, Any], planting: dict[str, Any]
) -> None:
    report = unredacted["report"]
    findings = [*report["hits"], *report["review"]]
    layer = planting["layer"]
    if layer in fx.TEXT_LAYERS:
        page = planting["page"]
        accepted = SUBSUMED.get((entity["id"], page, layer), {entity["id"]})
        assert any(
            f["layer"] == "page_text" and _in_band(f, page, layer) and _owner(f, entity, accepted)
            for f in findings
        ), (entity["id"], planting)
    elif layer == "metadata":
        field = planting["field"].capitalize()
        assert any(f["layer"] == "information_field" and f["field"] == field
                   and f["entry_id"] == entity["id"] for f in report["hits"])
    elif layer == "xmp":
        assert any(f["layer"] == "xmp" and f["entry_id"] == entity["id"] for f in report["hits"])
    elif layer == "embedded_file_name":
        assert any(f["layer"] == "embedded_file" and f["field"] == "name"
                   and f["entry_id"] == entity["id"] for f in report["hits"])
    else:  # pragma: no cover - a new layer needs a check
        pytest.fail(f"no check for layer {layer}")


def test_the_unredacted_fixture_fails(unredacted: dict[str, Any]) -> None:
    report = unredacted["report"]
    assert unredacted["result"].passed is False
    assert report["verdict"] == "fail"
    assert report["counts"]["hits"]["person_name"] > 0
    assert sum(report["counts"]["hits"].values()) == len(report["hits"])


def test_the_redacted_fixture_is_clean(redacted: dict[str, Any]) -> None:
    report = redacted["report"]
    assert report["hits"] == []
    assert redacted["result"].passed is True
    assert report["verdict"] == "pass"
    assert report["counts"]["hits"] == {}


def test_what_does_not_fail_is_listed_for_review(redacted: dict[str, Any]) -> None:
    # The niche topic waits for A3 and the model attack. "varnish" in a
    # reference title is the case-folded acronym the operator declared
    # case-sensitive: A2 kept it, the scan shows it, and neither fails.
    review = {(f["entry_id"], f["reason"], f["page"]) for f in redacted["report"]["review"]}
    assert review == {("E23", "flagged_category", 1), ("E18", "case_variant", 3)}


def test_countries_are_not_scanned(unredacted: dict[str, Any]) -> None:
    ids = {f["entry_id"] for f in [*unredacted["report"]["hits"], *unredacted["report"]["review"]]}
    assert ids.isdisjoint({"E14", "E15", "E31"})


# --------------------------------------------------------------------------- #
# What A2 does not edit, the scan still reads
# --------------------------------------------------------------------------- #


def _decorate(source: Path, target: Path) -> Path:
    """A copy of *source* carrying names in places A2 declares it does not edit."""
    doc = pymupdf.open(source)
    try:
        doc.set_toc([[1, "Vantrell group", 1]])
        page = doc[0]
        annot = page.add_text_annot((300, 300), "Ask Halvard Quist")
        annot.set_info(title="reviewer")
        annot.update()
        page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(72, 700, 200, 712),
                          "uri": "https://kelvara.example.org/team"})
        # Off the page: the default extraction clips it, the scan does not.
        page.insert_text((72, 900), "Fenwardt Biosystems GmbH", fontsize=8)
        xref = doc.xref_get_key(-1, "Info")[1].split()[0]
        # A custom key's name may itself identify, so it is reported by position.
        doc.xref_set_key(int(xref), "VantrellNotes", "(Department of Cryobiology)")
        doc.save(target, garbage=4, deflate=True, no_new_id=True)
    finally:
        doc.close()
    return target


def test_places_a2_does_not_edit_are_scanned(
    world: dict[str, Path], policy: ap.LoadedPolicy, redacted: dict[str, Any], tmp_path: Path
) -> None:
    decorated = _decorate(redacted["pdf"], tmp_path / "decorated.pdf")
    report = _report(_scan(world, policy, decorated, tmp_path / "scan"))
    found = {(h["layer"], h.get("field"), h["entry_id"] or h["regex_class"]) for h in report["hits"]}
    assert found == {
        ("outline", "title", "E01"),
        ("annotation", "content", "E02"),
        ("link", "uri", "url"),
        ("page_text", None, "E09"),
        ("information_field", "custom_1", "E08"),
    }
    assert report["verdict"] == "fail"


def test_a_name_in_an_xml_character_reference_is_found(
    world: dict[str, Path], policy: ap.LoadedPolicy, redacted: dict[str, Any], tmp_path: Path
) -> None:
    doc = pymupdf.open(redacted["pdf"])
    try:
        doc.set_xml_metadata("<x:xmpmeta xmlns:x='adobe:ns:meta/'>V&#225;ntrell</x:xmpmeta>")
        doc.save(tmp_path / "xmp.pdf", garbage=4, deflate=True, no_new_id=True)
    finally:
        doc.close()
    report = _report(_scan(world, policy, tmp_path / "xmp.pdf", tmp_path / "scan"))
    assert [(h["layer"], h["entry_id"]) for h in report["hits"]] == [("xmp", "E01")]


def test_an_embedded_file_description_is_scanned(
    world: dict[str, Path], policy: ap.LoadedPolicy, redacted: dict[str, Any], tmp_path: Path
) -> None:
    doc = pymupdf.open(redacted["pdf"])
    try:
        doc.embfile_upd(0, desc="notes from KELVARA")
        doc.save(tmp_path / "embedded.pdf", garbage=4, deflate=True, no_new_id=True)
    finally:
        doc.close()
    report = _report(_scan(world, policy, tmp_path / "embedded.pdf", tmp_path / "scan"))
    assert [(h["layer"], h["index"], h["field"], h["entry_id"]) for h in report["hits"]] == [
        ("embedded_file", 1, "description", "E10"),
    ]


# --------------------------------------------------------------------------- #
# 2. The mutation run
# --------------------------------------------------------------------------- #


#: Normalisations whose loss in A2 leaves a planted form the scan must catch.
#: ``case``, ``whitespace`` and ``initials`` are covered twice on this fixture
#: (every planting also matches another form), so switching one off leaves
#: nothing behind; the test asserts that too, so a fixture change shows here.
EXPOSED = {"diacritics", "line_break_hyphenation", "possessive"}


@pytest.mark.parametrize("normalisation", am.NORMALISATIONS)
def test_a_redaction_with_one_normalisation_off_fails_the_scan(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch, normalisation: str,
) -> None:
    def weakened(text: str, dictionary: am.EntityDictionary, **kwargs: Any) -> list[am.Match]:
        return am.find_matches(text, dictionary, disabled={normalisation})

    monkeypatch.setattr(ar, "find_matches", weakened)
    try:
        mutant = _redact(world, policy, tmp_path / "mutant")
    except ar.RedactionRefused:  # pragma: no cover - a refusal is not a leak
        pytest.fail(f"the redaction refused with {normalisation} off")
    monkeypatch.undo()
    result = _scan(world, policy, mutant.derivative, tmp_path / "scan")
    assert result.passed is (normalisation not in EXPOSED), _report(result)["hits"]


def test_the_scan_does_not_share_a2s_matcher_binding(
    world: dict[str, Path], policy: ap.LoadedPolicy, redacted: dict[str, Any],
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Weakening A2's binding leaves the scan's matcher whole.
    monkeypatch.setattr(ar, "find_matches", lambda *a, **k: [])
    result = _scan(world, policy, world["pdf"], tmp_path / "scan")
    assert result.passed is False


# --------------------------------------------------------------------------- #
# 3. The report: locations and categories, no private text
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
    texts.add(fx.PDF_NAME)
    # Below five characters a text is a code that may coincide with a key.
    return {t for t in texts if len(t) >= 5}


def test_the_report_quotes_no_private_text(unredacted: dict[str, Any]) -> None:
    text = unredacted["result"].report.read_text(encoding="utf-8").casefold()
    folded = " ".join(text.split())
    leaked = sorted(t for t in _texts_that_may_not_appear()
                    if t.casefold() in text or " ".join(t.casefold().split()) in folded)
    assert leaked == []


def test_every_finding_holds_locations_and_codes_only(unredacted: dict[str, Any]) -> None:
    allowed = {"layer", "page", "rects", "field", "index", "category", "entry_id",
               "regex_class", "form", "reason"}
    report = unredacted["report"]
    for finding in [*report["hits"], *report["review"]]:
        assert set(finding) <= allowed
        assert finding["layer"] in ls.LAYERS
        assert finding["entry_id"] is None or am.ENTRY_ID.match(finding["entry_id"])
    assert {h["category"] for h in report["hits"]} == {
        "person_name", "institution", "project_identity", "location", "facility",
        "dataset_cohort", "grant", "self_citation",
    }
    assert {h["layer"] for h in report["hits"]} == {
        "page_text", "information_field", "xmp", "embedded_file",
    }


def test_the_report_binds_its_input_policy_and_dictionary(
    world: dict[str, Path], policy: ap.LoadedPolicy, redacted: dict[str, Any]
) -> None:
    report = redacted["report"]
    assert report["schema"] == ls.SCHEMA
    assert report["stage"] == "A5"
    assert report["input"]["sha256"] == _sha(redacted["pdf"])
    assert report["policy_sha256"] == policy.sha256
    assert report["dictionary_sha256"] == ap.policy_sha256(fx.DICTIONARY)
    assert report["normalisations"] == list(am.NORMALISATIONS)
    assert report["coverage"]["scanned"] == list(ls.LAYERS)
    assert report["coverage"]["not_scanned"]


# --------------------------------------------------------------------------- #
# Replay and refusals
# --------------------------------------------------------------------------- #


def test_a_rescan_is_byte_equal_and_a_rescan_into_the_same_directory_is_a_no_op(
    world: dict[str, Path], policy: ap.LoadedPolicy, redacted: dict[str, Any], tmp_path: Path
) -> None:
    again = _scan(world, policy, redacted["pdf"], tmp_path / "again")
    assert again.report.read_bytes() == redacted["result"].report.read_bytes()
    before = redacted["result"].report.stat().st_mtime_ns
    _scan(world, policy, redacted["pdf"], redacted["result"].report.parent)
    assert redacted["result"].report.stat().st_mtime_ns == before


def test_a_different_report_is_never_written_over_one(
    world: dict[str, Path], policy: ap.LoadedPolicy, redacted: dict[str, Any]
) -> None:
    with pytest.raises(ls.LeakScanRefused, match="never overwritten"):
        _scan(world, policy, world["pdf"], redacted["result"].report.parent)


def test_a_dictionary_with_another_hash_is_refused(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path
) -> None:
    with pytest.raises(ls.LeakScanRefused, match="not the pinned dictionary"):
        _scan(world, policy, world["pdf"], tmp_path / "out", dictionary_sha256="0" * 64)
    assert not (tmp_path / "out").exists()


def test_a_policy_with_another_hash_is_refused(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path
) -> None:
    with pytest.raises(ap.PolicyChanged):
        _scan(world, policy, world["pdf"], tmp_path / "out", policy_sha256="0" * 64)
    assert not (tmp_path / "out").exists()


def test_an_unreadable_derivative_is_refused_without_naming_it(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path
) -> None:
    bad = tmp_path / "Vantrell_draft.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(ls.LeakScanRefused, match="cannot be opened") as refused:
        _scan(world, policy, bad, tmp_path / "out")
    assert "vantrell" not in str(refused.value).casefold()


@pytest.mark.parametrize("argument", ["derivative", "dictionary", "out_dir"])
def test_a_path_inside_the_repository_is_refused(
    world: dict[str, Path], policy: ap.LoadedPolicy, tmp_path: Path, argument: str
) -> None:
    inside = REPO / ".pytest_cache" / "an8a_must_not_exist"
    target = {"derivative": inside / fx.PDF_NAME, "dictionary": inside / "d.json",
              "out_dir": inside}
    if argument == "derivative":
        inside.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(world["pdf"], target["derivative"])
    try:
        with pytest.raises(ai.IntakeRefused, match="inside this repository"):
            _scan(world, policy, world["pdf"], tmp_path / "out", **{argument: target[argument]})
    finally:
        shutil.rmtree(inside, ignore_errors=True)
