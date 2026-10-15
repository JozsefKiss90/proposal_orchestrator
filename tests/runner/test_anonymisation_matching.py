"""AN5 — the entity dictionary and the text matcher behind stage A2.

Every normalisation the ticket names is shown to match, and to stop matching
when it is switched off, because AN8a's mutation run depends on that. Every
dictionary here is synthetic.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from runner import anonymisation_matching as am
from runner import anonymisation_policy as ap
from tests import _anonymisation_fixture as fx


@pytest.fixture(scope="module")
def policy() -> ap.LoadedPolicy:
    return ap.load(ap.STARTING_POLICY_PATH)


def _record(*entries: dict[str, Any]) -> dict[str, Any]:
    record = copy.deepcopy(fx.DICTIONARY)
    if entries:
        record["entries"] = list(entries)
    return record


def _dictionary(policy: ap.LoadedPolicy, *entries: dict[str, Any]) -> am.EntityDictionary:
    return am.validate_dictionary(_record(*entries), policy)


PERSON = fx._d("E01", "person_name", "Orsolya Vantrell", ["Supervisor S01", "S01"],
               person=fx._person("Orsolya", "Vantrell"))


def _found(text: str, d: am.EntityDictionary, *, disabled: tuple[str, ...] = ()) -> list[str]:
    return [text[m.start:m.end] for m in am.find_matches(text, d, disabled=disabled)]


# --------------------------------------------------------------------------- #
# Normalisations: each matches, and each can be switched off
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("normalisation", "text", "expected"),
    [
        ("case", "ORSOLYA VANTRELL", "ORSOLYA VANTRELL"),
        ("diacritics", "Prof. Orsolya Vántrell spoke", "Orsolya Vántrell"),
        ("whitespace", "Orsolya\nVantrell", "Orsolya\nVantrell"),
        ("line_break_hyphenation", "Prof. Orsolya Vant-\nrell, built", "Orsolya Vant-\nrell"),
        ("possessive", "O. Vantrell's grant", "O. Vantrell"),
        ("initials", "Vantrell, O. (2021)", "Vantrell, O."),
    ],
)
def test_each_normalisation_matches_and_can_be_disabled(
    policy: ap.LoadedPolicy, normalisation: str, text: str, expected: str
) -> None:
    person = {**PERSON, "person": {**PERSON["person"], "match_family_alone": False}}
    d = _dictionary(policy, person)
    assert _found(text, d) == [expected]
    assert _found(text, d, disabled=(normalisation,)) == []


def test_the_normalisations_are_the_ones_the_ticket_names() -> None:
    assert set(am.NORMALISATIONS) == {
        "case", "diacritics", "whitespace", "line_break_hyphenation", "possessive", "initials",
    }


def test_an_unknown_normalisation_is_refused(policy: ap.LoadedPolicy) -> None:
    with pytest.raises(ValueError):
        am.find_matches("x", _dictionary(policy), disabled=("stemming",))


def test_a_compound_hyphen_at_a_line_end_still_matches(policy: ap.LoadedPolicy) -> None:
    d = _dictionary(policy, fx._d("E11", "project_identity", "Kelp-Derived Lichen", ["T"]))
    assert _found("the Kelp-\nDerived Lichen work", d) == ["Kelp-\nDerived Lichen"]


def test_a_person_matches_in_both_orders_and_by_family_name(policy: ap.LoadedPolicy) -> None:
    d = _dictionary(policy, PERSON)
    assert _found("Vantrell Orsolya wrote", d) == ["Vantrell Orsolya"]
    assert _found("Prof. Vantrell wrote", d) == ["Vantrell"]
    alone_off = {**PERSON, "person": {**PERSON["person"], "match_family_alone": False}}
    assert _found("Prof. Vantrell wrote", _dictionary(policy, alone_off)) == []


def test_a_name_inside_a_longer_word_is_not_matched(policy: ap.LoadedPolicy) -> None:
    d = _dictionary(policy, fx._d("E18", "grant", "VARNISH", ["a grant"]))
    assert _found("the varnishes dried", d) == []
    assert _found("kelvara_varnish_notes", d) == ["varnish"]


def test_match_case_keeps_a_word_that_shares_an_acronym(policy: ap.LoadedPolicy) -> None:
    d = _dictionary(policy, fx._d("E18", "grant", "VARNISH", ["a grant"], match_case=True))
    assert _found("Lichen varnish under the VARNISH grant", d) == ["VARNISH"]


# --------------------------------------------------------------------------- #
# Patterns and overlaps
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("regex_class", "text", "expected"),
    [
        ("doi", "see doi:10.5555/kelvara.2021.001.", "10.5555/kelvara.2021.001"),
        ("grant_number", "grant agreement No 109999417)", "109999417"),
        ("orcid", "ORCID 0000-0002-1825-0097,", "0000-0002-1825-0097"),
        ("email", "write to o.vantrell@kelpmoor.example.org, now", "o.vantrell@kelpmoor.example.org"),
        ("url", "at https://kelvara.example.org.", "https://kelvara.example.org"),
        ("phone", "call +358 9 555 0142, or", "+358 9 555 0142"),
    ],
)
def test_each_regex_class_matches_without_trailing_punctuation(
    policy: ap.LoadedPolicy, regex_class: str, text: str, expected: str
) -> None:
    matches = am.find_matches(text, _dictionary(policy, fx._d("E99", "grant", "ZZQX", ["a"])))
    assert [(text[m.start:m.end], m.regex_class) for m in matches] == [(expected, regex_class)]


@pytest.mark.parametrize(
    ("regex_class", "text", "expected"),
    [
        ("url", "at https://kelvara.exam-\nple.org now", "https://kelvara.exam-\nple.org"),
        ("url", "at https://kelvara.example.org/\npath now", "https://kelvara.example.org/\npath"),
        ("doi", "doi:10.5555/kel-\nvara.2021.001 x", "10.5555/kel-\nvara.2021.001"),
        ("email", "o.vantrell@kelp-\nmoor.example.org x", "o.vantrell@kelp-\nmoor.example.org"),
        ("grant_number", "No 109 999 417.", "109 999 417"),
    ],
)
def test_a_wrapped_or_spaced_identifier_is_caught_whole(
    policy: ap.LoadedPolicy, regex_class: str, text: str, expected: str
) -> None:
    d = _dictionary(policy, fx._d("E99", "grant", "ZZQX", ["a"]))
    assert [(text[m.start:m.end], m.regex_class) for m in am.find_matches(text, d)] == [
        (expected, regex_class)]
    if "\n" in expected:
        assert all(m.end - m.start < len(expected) for m in am.find_matches(
            text, d, disabled=("line_break_hyphenation",)))


def test_a_hyphenated_given_name_has_hyphenated_initials(policy: ap.LoadedPolicy) -> None:
    person = fx._d("E40", "person_name", "Jean-Pierre Kiss", ["S04"],
                   person={"given": "Jean-Pierre", "family": "Kiss",
                           "match_family_alone": False})
    d = _dictionary(policy, person)
    assert _found("by J.-P. Kiss and J. Kiss", d) == ["J.-P. Kiss", "J. Kiss"]


def test_a_dictionary_inside_the_repository_is_refused(policy: ap.LoadedPolicy) -> None:
    with pytest.raises(am.DictionaryRefused, match="inside this repository"):
        am.load_dictionary(ap.STARTING_POLICY_PATH, policy)


def test_the_longest_leftmost_match_wins(policy: ap.LoadedPolicy) -> None:
    d = _dictionary(policy)
    text = "at the Brennmark Tidal Flux Observatory, and o.vantrell@kelpmoor.example.org"
    matches = am.find_matches(text, d)
    assert [(m.entry_id, m.regex_class) for m in matches] == [("E16", None), (None, "email")]


def test_kept_entries_are_not_matched_and_flagged_ones_are_marked(policy: ap.LoadedPolicy) -> None:
    d = _dictionary(policy)
    text = ("Finland and cryo-electron tomography of lichen photobionts in\n"
            "high-altitude permafrost")
    matches = am.find_matches(text, d)
    assert [(m.entry_id, m.action, m.replacements) for m in matches] == [("E23", "flag", ())]


# --------------------------------------------------------------------------- #
# The dictionary
# --------------------------------------------------------------------------- #


def test_the_fixture_dictionary_validates_and_its_hash_ignores_layout(
    policy: ap.LoadedPolicy, tmp_path: Path
) -> None:
    d = am.load_dictionary(fx.write_dictionary(tmp_path), policy)
    indented = tmp_path / "other.json"
    indented.write_text(json.dumps(fx.DICTIONARY, indent=7), encoding="utf-8")
    assert am.load_dictionary(indented, policy).sha256 == d.sha256
    assert d.policy_sha256 == policy.sha256
    assert {e.action for e in d.entries} == {"edit", "flag", "keep"}


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (lambda r: r["entries"][0].update(id="Vantrell"), "id is not a code"),
        (lambda r: r["entries"][0].update(category="people"), "not a policy category"),
        (lambda r: r["entries"][0].update(replacements=["", "S01"]), "may only come last"),
        (lambda r: r["entries"][0].update(replacements=[]), "non-empty list"),
        (lambda r: r["entries"][0].update(country=True), "only a location"),
        (lambda r: r["entries"][-1].update(replacements=["x"]), "takes no replacement"),
        (lambda r: r["entries"][1].update(id="E01"), "id repeated"),
        (lambda r: r["entries"][3].update(person=fx._person("A", "B")), "only a person_name"),
        (lambda r: r["entries"][0].update(match_case="yes"), "match_case"),
        (lambda r: r["regex_classes"].pop("phone"), "regex_classes must name"),
        (lambda r: r["regex_classes"]["doi"].update(category="niche_topic"), "auto-edited"),
        (lambda r: r.update(schema="other/1"), "schema"),
    ],
)
def test_a_malformed_dictionary_is_refused(
    policy: ap.LoadedPolicy, change: Any, problem: str
) -> None:
    record = _record()
    change(record)
    with pytest.raises(am.DictionaryRefused) as refused:
        am.validate_dictionary(record, policy)
    assert problem in str(refused.value)


def test_a_replacement_that_would_be_redacted_is_refused(policy: ap.LoadedPolicy) -> None:
    record = _record()
    record["entries"][3]["replacements"] = ["Beneficiary B1 near Brennmark"]
    with pytest.raises(am.DictionaryRefused, match="would itself be redacted"):
        am.validate_dictionary(record, policy)


def test_a_replacement_may_name_a_kept_country(policy: ap.LoadedPolicy) -> None:
    record = _record()
    record["entries"][8]["replacements"] = ["a coastal town in Finland", "a town"]
    am.validate_dictionary(record, policy)


def test_a_refusal_quotes_no_surface_form(policy: ap.LoadedPolicy) -> None:
    record = _record()
    for entry in record["entries"]:
        entry["replacements"] = ["", "x"] if entry["replacements"] else []
    with pytest.raises(am.DictionaryRefused) as refused:
        am.validate_dictionary(record, policy)
    message = str(refused.value).casefold()
    for entry in fx.DICTIONARY["entries"]:
        assert entry["surface"].casefold() not in message


def test_an_unreadable_dictionary_names_no_path(policy: ap.LoadedPolicy, tmp_path: Path) -> None:
    secret = tmp_path / "kelvara_dictionary.json"
    secret.write_text("{", encoding="utf-8")
    with pytest.raises(am.DictionaryRefused) as refused:
        am.load_dictionary(secret, policy)
    assert "kelvara" not in str(refused.value)
