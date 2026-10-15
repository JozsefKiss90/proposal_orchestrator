"""AN9 — structural fidelity comparison (stage A6 of the anonymisation pipeline).

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN9:

1. Comparing the fixture with its redacted derivative reports differences per
   category.
2. A difference the policy does not explain is a finding, not a pass.
3. A figure whose only basis is a measurement is refused as preserved,
   consistent with the V08 acceptance check.

The end-to-end tests run A0, A2 and A4 on the synthetic fixture and compare.
The rule tests call :func:`compare` on the fixture's own reference inventory,
copied and changed in one place, so each test names the one difference it is
about.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import anonymisation_fidelity as af  # noqa: E402
from runner import anonymisation_intake as ai  # noqa: E402
from runner import anonymisation_policy as ap  # noqa: E402
from runner import anonymisation_redaction as ar  # noqa: E402
from runner import anonymisation_table as at  # noqa: E402
from runner import dry_import as di  # noqa: E402
from tests import _anonymisation_fixture as fx  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

#: The fixture's graphical pages: the logo, the supervisor table's rules and
#: the diagram.
GRAPHICAL_PAGES = [1, 2, 3]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def policy() -> ap.LoadedPolicy:
    return ap.load(ap.STARTING_POLICY_PATH)


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory, policy: ap.LoadedPolicy) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("an9")
    built = fx.build(root / "fixture")
    intake = ai.intake(pdf=built.pdf, expected_sha256=_sha(built.pdf), out_dir=root / "intake")
    private = root / "private"
    dictionary = fx.write_dictionary(private)
    redacted = ar.redact(
        pdf=built.pdf,
        intake_record=intake.intake_record,
        policy=policy,
        policy_sha256=policy.sha256,
        dictionary=dictionary,
        dictionary_sha256=ap.policy_sha256(fx.DICTIONARY),
        out_dir=root / "a2",
    )
    spec = fx.write_table_spec(private)
    synthesised = at.synthesise(
        derivative=redacted.derivative,
        redaction_log=redacted.edit_log,
        intake_record=intake.intake_record,
        policy=policy,
        policy_sha256=policy.sha256,
        dictionary=dictionary,
        dictionary_sha256=ap.policy_sha256(fx.DICTIONARY),
        spec=spec,
        spec_sha256=ap.policy_sha256(fx.TABLE_SPEC),
        out_dir=root / "a4",
    )
    return {
        "root": root,
        "source": built.pdf,
        "intake": intake,
        "redacted": redacted,
        "synthesised": synthesised,
        "reference": json.loads(intake.reference_inventory.read_text(encoding="utf-8")),
    }


def _review(sha256: str, pages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": af.REVIEW_SCHEMA,
        "record_type": af.REVIEW_RECORD_TYPE,
        "derivative_sha256": sha256,
        "pages": pages,
    }


def _looked_at(page: int, verdict: str = "preserved",
               basis: str = "operator_visual_comparison") -> dict[str, Any]:
    return {"page": page, "verdict": verdict, "basis": basis, "reviewed_by": "operator",
            "reviewed_on": "2026-10-16", "note": ""}


def _write_review(path: Path, record: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def _fidelity(world: dict[str, Any], policy: ap.LoadedPolicy, out: Path,
              **overrides: Any) -> af.FidelityResult:
    kwargs: dict[str, Any] = {
        "derivative": world["synthesised"].derivative,
        "derivative_sha256": world["synthesised"].derivative_sha256,
        "intake_record": world["intake"].intake_record,
        "policy": policy,
        "policy_sha256": policy.sha256,
        "stage_logs": [world["redacted"].edit_log, world["synthesised"].log],
        "figure_review": None,
        "out_dir": out,
    }
    kwargs.update(overrides)
    return af.fidelity(**kwargs)


def _report(result: af.FidelityResult) -> dict[str, Any]:
    return json.loads(result.report.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def unreviewed(world: dict[str, Any], policy: ap.LoadedPolicy) -> dict[str, Any]:
    return _report(_fidelity(world, policy, world["root"] / "a6_unreviewed"))


def _of(report: dict[str, Any], category: str, **where: Any) -> list[dict[str, Any]]:
    return [
        d for d in report["differences"]
        if d["category"] == category and all(d.get(k) == v for k, v in where.items())
    ]


# --------------------------------------------------------------------------- #
# Criterion 1: differences reported per category
# --------------------------------------------------------------------------- #


def test_every_compared_category_is_counted(unreviewed: dict[str, Any]) -> None:
    assert list(unreviewed["counts"]) == list(af.CATEGORIES)
    for counts in unreviewed["counts"].values():
        assert set(counts) == {"differences", "explained", "findings"}


def test_the_fixture_keeps_its_page_count_headings_and_tables(unreviewed: dict[str, Any]) -> None:
    for category in ("page_count", "headings", "tables"):
        assert unreviewed["counts"][category] == {"differences": 0, "explained": 0, "findings": 0}


def test_removed_identifiers_are_explained_by_the_logged_edits(unreviewed: dict[str, Any]) -> None:
    doi = _of(unreviewed, "citation_markers", marker_class="doi")
    url = _of(unreviewed, "citation_markers", marker_class="url")
    assert doi and url
    for difference in doi + url:
        assert difference["derivative"] < difference["reference"]
        assert difference["status"] == "explained"
        assert difference["explanation"]["edits"]


def test_neutral_markers_are_explained_by_self_citation_edits(unreviewed: dict[str, Any]) -> None:
    labels = _of(unreviewed, "citation_markers", marker_class="bracketed_labels")
    assert [(d["page"], d["reference"], d["derivative"]) for d in labels] == [(3, 0, 2)]
    assert labels[0]["status"] == "explained"
    assert "self_citation" in labels[0]["explanation"]["categories"]


def test_every_citation_difference_on_the_fixture_is_explained(unreviewed: dict[str, Any]) -> None:
    counts = unreviewed["counts"]["citation_markers"]
    assert counts["differences"] > 0
    assert counts["findings"] == 0


def test_the_fixture_keeps_every_point_size(unreviewed: dict[str, Any]) -> None:
    """A2 writes each replacement at its span's own size, so no size appears or goes."""
    assert unreviewed["counts"]["point_sizes"] == {"differences": 0, "explained": 0,
                                                   "findings": 0}


def test_an_unreviewed_figure_is_a_finding_even_when_its_counts_match(
    unreviewed: dict[str, Any],
) -> None:
    assert [f["page"] for f in unreviewed["figures"]] == GRAPHICAL_PAGES
    for figure in unreviewed["figures"]:
        assert figure["counts_equal"] is True
        assert figure["status"] == "finding"
        assert figure["code"] == "figure_not_looked_at"
    assert unreviewed["counts"]["figures"]["findings"] == len(GRAPHICAL_PAGES)


def test_the_derivative_inventory_is_written_beside_the_report(
    world: dict[str, Any], policy: ap.LoadedPolicy,
) -> None:
    result = _fidelity(world, policy, world["root"] / "a6_inventory")
    stored = json.loads(result.derivative_inventory.read_text(encoding="utf-8"))
    assert stored["sha256"] == world["synthesised"].derivative_sha256
    assert _report(result)["input"]["derivative_inventory_sha256"] == _sha(
        result.derivative_inventory
    )


# --------------------------------------------------------------------------- #
# Criterion 2: an unexplained difference is a finding
# --------------------------------------------------------------------------- #


def _edit(page: int, category: str | None = "person_name", regex_class: str | None = None,
          stage: str = "A2", edit: int = 0) -> af.LoggedEdit:
    return af.LoggedEdit(stage=stage, edit=edit, page=page, category=category,
                         regex_class=regex_class)


def _compare(world: dict[str, Any], policy: ap.LoadedPolicy, derivative: dict[str, Any],
             edits: list[af.LoggedEdit] | None = None,
             review: dict[str, Any] | None = None) -> dict[str, Any]:
    return af.compare(world["reference"], derivative, edits=edits or [], policy=policy,
                      review=review)


def _findings(result: dict[str, Any], category: str) -> list[dict[str, Any]]:
    return [d for d in result["differences"] if d["category"] == category
            and d["status"] == "finding"]


def test_an_identical_inventory_has_no_difference(world, policy) -> None:
    result = _compare(world, policy, copy.deepcopy(world["reference"]))
    assert result["differences"] == []


def test_a_changed_page_count_is_a_finding(world, policy) -> None:
    derivative = copy.deepcopy(world["reference"])
    derivative["pages"] += 1
    [finding] = _findings(_compare(world, policy, derivative), "page_count")
    assert finding["code"] == "page_count_changed"


def test_a_heading_moved_to_another_page_is_a_finding(world, policy) -> None:
    derivative = copy.deepcopy(world["reference"])
    heading = derivative["heading_candidates"][0]
    heading["page"] += 1
    result = _compare(world, policy, derivative, [_edit(heading["page"])])
    [finding] = _findings(result, "headings")
    assert finding["code"] == "heading_moved"


def test_a_heading_text_change_needs_an_edit_on_its_page(world, policy) -> None:
    derivative = copy.deepcopy(world["reference"])
    heading = derivative["heading_candidates"][0]
    heading["text"] += " changed"
    page = heading["page"]

    [finding] = _findings(_compare(world, policy, derivative, [_edit(page + 1)]), "headings")
    assert finding["code"] == "heading_text_changed_without_edit"

    explained = _compare(world, policy, derivative, [_edit(page)])
    [difference] = [d for d in explained["differences"] if d["category"] == "headings"]
    assert difference["status"] == "explained"
    assert difference["explanation"]["categories"] == ["person_name"]


def test_an_edit_the_policy_does_not_authorise_explains_nothing(world, policy) -> None:
    """``niche_topic`` is flagged, not edited, so an edit in its name is no explanation."""
    derivative = copy.deepcopy(world["reference"])
    heading = derivative["heading_candidates"][0]
    heading["text"] += " changed"
    result = _compare(world, policy, derivative, [_edit(heading["page"], "niche_topic")])
    assert _findings(result, "headings")


def test_a_changed_table_shape_is_a_finding(world, policy) -> None:
    derivative = copy.deepcopy(world["reference"])
    table = derivative["tables"]["per_table"][0]
    table["rows"] -= 1
    result = _compare(world, policy, derivative, [_edit(table["page"])])
    [finding] = _findings(result, "tables")
    assert finding["code"] == "table_shape_changed"


def test_a_lost_table_is_a_finding(world, policy) -> None:
    derivative = copy.deepcopy(world["reference"])
    derivative["tables"]["per_table"] = []
    [finding] = _findings(_compare(world, policy, derivative), "tables")
    assert finding["code"] == "table_count_changed"


def test_a_size_the_reference_does_not_carry_is_a_finding(world, policy) -> None:
    """Replacement text set smaller than its span: no policy rule changes a point size."""
    derivative = copy.deepcopy(world["reference"])
    derivative["point_sizes"]["distribution"]["8.5"] = 12
    [finding] = _findings(_compare(world, policy, derivative), "point_sizes")
    assert finding["code"] == "size_absent_from_reference"
    assert (finding["size"], finding["derivative"]) == ("8.5", 12)


def test_a_changed_body_size_is_a_finding(world, policy) -> None:
    derivative = copy.deepcopy(world["reference"])
    derivative["point_sizes"]["largest_share"]["size"] = "9.0"
    findings = _findings(_compare(world, policy, derivative), "point_sizes")
    assert "body_size_changed" in {f["code"] for f in findings}


def _set_citations(inventory: dict[str, Any], page: int, **counts: int) -> None:
    row = next(r for r in inventory["citation_markers"]["per_page"] if r["page"] == page)
    row["counts"].update(counts)


def _citation_page(world: dict[str, Any], marker_class: str) -> tuple[int, int]:
    for row in world["reference"]["citation_markers"]["per_page"]:
        if row["counts"][marker_class]:
            return row["page"], row["counts"][marker_class]
    raise AssertionError(f"the fixture carries no {marker_class}")


def test_an_identifier_removed_without_an_edit_is_a_finding(world, policy) -> None:
    page, n = _citation_page(world, "doi")
    derivative = copy.deepcopy(world["reference"])
    _set_citations(derivative, page, doi=n - 1)
    [finding] = _findings(_compare(world, policy, derivative), "citation_markers")
    assert finding["code"] == "citation_removed_without_edit"

    explained = _compare(world, policy, derivative,
                         [_edit(page, "self_citation", regex_class="doi")])
    assert not _findings(explained, "citation_markers")


def test_a_lost_citation_marker_is_a_finding_whatever_was_edited(world, policy) -> None:
    """The policy keeps the count of citation markers, so a marker that is not
    replaced by a neutral marker on its own page is lost."""
    page, n = _citation_page(world, "bracketed_numbers")
    derivative = copy.deepcopy(world["reference"])
    _set_citations(derivative, page, bracketed_numbers=n - 1)
    result = _compare(world, policy, derivative, [_edit(page, "self_citation")])
    [finding] = _findings(result, "citation_markers")
    assert finding["code"] == "citation_marker_lost"


def test_a_marker_replaced_by_a_neutral_marker_is_explained(world, policy) -> None:
    page, n = _citation_page(world, "bracketed_numbers")
    derivative = copy.deepcopy(world["reference"])
    labels = next(r for r in derivative["citation_markers"]["per_page"]
                  if r["page"] == page)["counts"]["bracketed_labels"]
    _set_citations(derivative, page, bracketed_numbers=n - 1, bracketed_labels=labels + 1)
    result = _compare(world, policy, derivative, [_edit(page, "self_citation")])
    assert not _findings(result, "citation_markers")
    assert {d["marker_class"] for d in result["differences"]} == {
        "bracketed_numbers", "bracketed_labels"}


def test_more_neutral_markers_than_lost_markers_is_a_finding(world, policy) -> None:
    """The count is kept only when each lost marker has exactly one neutral marker."""
    page, n = _citation_page(world, "bracketed_numbers")
    derivative = copy.deepcopy(world["reference"])
    labels = next(r for r in derivative["citation_markers"]["per_page"]
                  if r["page"] == page)["counts"]["bracketed_labels"]
    _set_citations(derivative, page, bracketed_numbers=n - 1, bracketed_labels=labels + 3)
    edits = [_edit(page, "self_citation", edit=k) for k in range(3)]
    codes = {f["code"] for f in _findings(_compare(world, policy, derivative, edits),
                                          "citation_markers")}
    assert "citation_marker_lost" in codes


def test_a_table_edit_does_not_explain_a_changed_heading(world, policy) -> None:
    derivative = copy.deepcopy(world["reference"])
    heading = derivative["heading_candidates"][0]
    heading["text"] += " changed"
    result = _compare(world, policy, derivative,
                      [_edit(heading["page"], None, stage="A4")])
    assert _findings(result, "headings")


def test_a_marker_moved_to_another_page_is_a_finding(world, policy) -> None:
    page, n = _citation_page(world, "bracketed_numbers")
    other = next(p for p in range(1, world["reference"]["pages"] + 1) if p != page)
    derivative = copy.deepcopy(world["reference"])
    _set_citations(derivative, page, bracketed_numbers=n - 1)
    before = next(r for r in derivative["citation_markers"]["per_page"]
                  if r["page"] == other)["counts"]["bracketed_numbers"]
    _set_citations(derivative, other, bracketed_numbers=before + 1)
    codes = {f["code"] for f in _findings(_compare(world, policy, derivative),
                                          "citation_markers")}
    assert codes == {"citation_marker_lost", "citation_added"}


def test_a_report_with_a_finding_fails(world, policy) -> None:
    derivative = copy.deepcopy(world["reference"])
    derivative["pages"] += 1
    review = _review("x", [_looked_at(p) for p in GRAPHICAL_PAGES])
    assert _compare(world, policy, derivative, review=review)["verdict"] == "fail"
    assert _compare(world, policy, copy.deepcopy(world["reference"]),
                    review=review)["verdict"] == "pass"


# --------------------------------------------------------------------------- #
# Criterion 3: a figure is looked at, not counted
# --------------------------------------------------------------------------- #


def _figure(result: dict[str, Any], page: int) -> dict[str, Any]:
    return next(f for f in result["figures"] if f["page"] == page)


@pytest.mark.parametrize("basis", sorted(di.MEASUREMENT_ONLY_BASES))
def test_a_figure_preserved_on_a_measurement_is_refused(world, policy, basis: str) -> None:
    review = _review("x", [_looked_at(1, basis=basis)])
    figure = _figure(_compare(world, policy, copy.deepcopy(world["reference"]),
                              review=review), 1)
    assert figure["status"] == "finding"
    assert figure["code"] == "measurement_basis_not_proof"


def test_a_figure_looked_at_and_unchanged_is_preserved(world, policy) -> None:
    review = _review("x", [_looked_at(1)])
    figure = _figure(_compare(world, policy, copy.deepcopy(world["reference"]),
                              review=review), 1)
    assert figure["status"] == "preserved"
    assert "code" not in figure


def test_a_masked_figure_is_explained_by_the_policy(world, policy) -> None:
    derivative = copy.deepcopy(world["reference"])
    derivative["per_page"][0]["images"] = 0
    review = _review("x", [_looked_at(1, verdict="masked")])
    result = _compare(world, policy, derivative, review=review)
    figure = _figure(result, 1)
    assert figure["status"] == "explained"
    assert figure["explanation"]["categories"] == ["identifying_figure"]
    assert result["counts"]["figures"]["differences"] == 1


def test_a_figure_declared_preserved_whose_counts_changed_is_a_finding(world, policy) -> None:
    derivative = copy.deepcopy(world["reference"])
    derivative["per_page"][2]["drawings"] += 1
    review = _review("x", [_looked_at(3)])
    figure = _figure(_compare(world, policy, derivative, review=review), 3)
    assert figure["code"] == "preserved_but_counts_changed"


def test_a_lost_figure_is_a_finding(world, policy) -> None:
    derivative = copy.deepcopy(world["reference"])
    derivative["per_page"][2]["drawings"] = 0
    review = _review("x", [_looked_at(3, verdict="lost", basis="zero_embedded_images")])
    assert _figure(_compare(world, policy, derivative, review=review), 3)["code"] == "figure_lost"


def test_an_action_the_policy_does_not_permit_is_a_finding(world, policy) -> None:
    narrow = dataclasses.replace(policy, categories=tuple(
        dataclasses.replace(c, permitted_actions=("redraw",))
        if c.id == "identifying_figure" else c
        for c in policy.categories
    ))
    review = _review("x", [_looked_at(1, verdict="masked")])
    figure = _figure(af.compare(world["reference"], copy.deepcopy(world["reference"]),
                                edits=[], policy=narrow, review=review), 1)
    assert figure["code"] == "action_not_permitted"


@pytest.mark.parametrize(
    "change, code",
    [
        ({"basis": "it looked fine"}, "unknown_basis"),
        ({"verdict": "kept"}, "unknown_verdict"),
        ({"reviewed_by": None}, "verdict_without_attestation"),
    ],
)
def test_a_malformed_review_entry_is_a_finding(world, policy, change, code) -> None:
    entry = {**_looked_at(1), **change}
    figure = _figure(_compare(world, policy, copy.deepcopy(world["reference"]),
                              review=_review("x", [entry])), 1)
    assert figure["code"] == code


# --------------------------------------------------------------------------- #
# The file-level run
# --------------------------------------------------------------------------- #


def test_a_review_of_every_figure_passes_the_fixture(
    world: dict[str, Any], policy: ap.LoadedPolicy,
) -> None:
    sha = world["synthesised"].derivative_sha256
    review = _write_review(world["root"] / "private" / "figure_review.json",
                           _review(sha, [_looked_at(p) for p in GRAPHICAL_PAGES]))
    result = _fidelity(world, policy, world["root"] / "a6_reviewed", figure_review=review)
    report = _report(result)
    assert result.passed is True
    assert report["verdict"] == "pass"
    assert [f["status"] for f in report["figures"]] == ["preserved"] * 3
    assert report["input"]["figure_review_sha256"] == _sha(review)


def test_a_review_of_another_derivative_is_refused(world, policy) -> None:
    review = _write_review(world["root"] / "private" / "other_review.json",
                           _review("0" * 64, [_looked_at(1)]))
    with pytest.raises(af.FidelityRefused, match="another derivative"):
        _fidelity(world, policy, world["root"] / "a6_other_review", figure_review=review)


def test_a_review_naming_a_page_twice_is_refused(world, policy) -> None:
    sha = world["synthesised"].derivative_sha256
    review = _write_review(world["root"] / "private" / "twice.json",
                           _review(sha, [_looked_at(1), _looked_at(1)]))
    with pytest.raises(af.FidelityRefused, match="twice"):
        _fidelity(world, policy, world["root"] / "a6_twice", figure_review=review)


def test_the_redacted_stage_alone_compares(world, policy) -> None:
    result = _fidelity(
        world, policy, world["root"] / "a6_a2_only",
        derivative=world["redacted"].derivative,
        derivative_sha256=world["redacted"].derivative_sha256,
        stage_logs=[world["redacted"].edit_log],
    )
    assert _report(result)["counts"]["citation_markers"]["findings"] == 0


def test_a_broken_stage_chain_is_refused(world, policy) -> None:
    with pytest.raises(af.FidelityRefused, match="chain"):
        _fidelity(world, policy, world["root"] / "a6_chain",
                  stage_logs=[world["synthesised"].log])


def test_a_derivative_that_is_not_the_last_stage_output_is_refused(world, policy) -> None:
    with pytest.raises(af.FidelityRefused, match="chain"):
        _fidelity(world, policy, world["root"] / "a6_last",
                  derivative=world["redacted"].derivative,
                  derivative_sha256=world["redacted"].derivative_sha256)


def test_a_derivative_off_its_pin_is_refused(world, policy) -> None:
    with pytest.raises(ai.IntakeRefused):
        _fidelity(world, policy, world["root"] / "a6_pin", derivative_sha256="0" * 64)


def test_a_policy_other_than_the_stages_is_refused(world, policy) -> None:
    record = copy.deepcopy(policy.record)
    record["policy_version"] = 2
    other = dataclasses.replace(policy, record=record, sha256=ap.policy_sha256(record),
                                version=2)
    with pytest.raises(af.FidelityRefused, match="policy"):
        _fidelity(world, other, world["root"] / "a6_policy",
                  policy_sha256=other.sha256)


def test_a_tampered_reference_inventory_is_refused(world, policy, tmp_path_factory) -> None:
    root = tmp_path_factory.mktemp("an9_tamper")
    shutil.copytree(world["intake"].intake_record.parent, root / "intake")
    inventory = root / "intake" / ai.REFERENCE_INVENTORY_FILE
    inventory.write_text(inventory.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(af.FidelityRefused, match="reference inventory"):
        _fidelity(world, policy, root / "a6",
                  intake_record=root / "intake" / ai.INTAKE_RECORD_FILE)


def test_an_unknown_stage_log_is_refused(world, policy) -> None:
    bad = world["root"] / "private" / "unknown_log.json"
    bad.write_text(json.dumps({"schema": "something_else/1"}), encoding="utf-8")
    with pytest.raises(af.FidelityRefused, match="stage log"):
        _fidelity(world, policy, world["root"] / "a6_unknown", stage_logs=[bad])


@pytest.mark.parametrize("argument", ["derivative", "out_dir", "figure_review"])
def test_a_path_inside_the_repository_is_refused(world, policy, argument: str) -> None:
    with pytest.raises(ai.IntakeRefused, match="inside this repository"):
        _fidelity(world, policy, world["root"] / "unused",
                  **{argument: REPO / "fidelity_inside.json"})


def test_a_rerun_is_a_no_op_and_a_different_report_is_refused(world, policy) -> None:
    out = world["root"] / "a6_rerun"
    first = _report(_fidelity(world, policy, out))
    assert _report(_fidelity(world, policy, out)) == first
    sha = world["synthesised"].derivative_sha256
    review = _write_review(world["root"] / "private" / "rerun_review.json",
                           _review(sha, [_looked_at(1)]))
    with pytest.raises(af.FidelityRefused, match="never overwritten"):
        _fidelity(world, policy, out, figure_review=review)


def test_the_report_quotes_no_heading_or_table_text(
    world: dict[str, Any], unreviewed: dict[str, Any],
) -> None:
    dumped = json.dumps(unreviewed, ensure_ascii=False)
    reference = world["reference"]
    quoted = [h["text"] for h in reference["heading_candidates"]]
    quoted += [cell for t in reference["tables"]["per_table"] for cell in t["header"] if cell]
    assert quoted
    for text in quoted:
        assert text not in dumped
    for entry in fx.DICTIONARY["entries"]:
        assert entry["surface"] not in dumped
