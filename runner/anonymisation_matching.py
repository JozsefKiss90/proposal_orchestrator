"""The entity dictionary and the text matcher of the anonymisation pipeline.

Stage A2 of ``plans/msca_dn_anonymisation_handoff_2026-10-14.md`` (AN5)
applies the operator's **entity dictionary** to the document, and stage A5's
leak scan (AN8a) looks for the same entries in the derivative. Both need the
same answer to one question: where in this text does a dictionary entry or an
identifier pattern occur? This module answers it, on plain text, with no PDF
and no model.

The entity dictionary
---------------------
``anonymisation_entity_dictionary/1``, authored privately by the operator
(handoff §5 A1). Each entry names a concrete entity, its policy category, the
surface forms it takes and its replacements in order of preference. The
dictionary's hash is taken like the policy's (:func:`runner.anonymisation_policy.policy_sha256`),
so a re-indent does not change it. An entry id is written to the edit log, so
it is a short code (:data:`ENTRY_ID`) and can never carry a name.

What the policy does to an entry:

* a category with ``auto_edit`` false (niche topics, figures) is **flagged**:
  matched and located for A3 and A5, never edited, and given no replacement;
* a location entry marked ``country`` is **kept**: the policy retains the
  country (O4), so it is not matched at all;
* every other entry is **edited** with its first replacement that fits.

An empty replacement removes the text. It is admissible only as an entry's
last replacement, so a removal is always the operator's declared choice.

Normalisation
-------------
Matching folds both the text and the surface forms, then compiles each form
into a pattern. Each of :data:`NORMALISATIONS` can be switched off, so AN8a's
mutation run can show that the leak scan depends on it:

``case``
    case-insensitive, by ``str.casefold``. An entry that declares
    ``match_case`` is matched with its case, because an acronym that is also
    a word ("VARNISH") would otherwise replace the word. A leak scan should
    ignore the flag, so that a "Varnish" A2 left is still found.
``diacritics``
    compatibility decomposition with combining marks dropped, so "Vántrell"
    matches "Vantrell".
``whitespace``
    a space in a surface form matches any run of whitespace, line breaks
    included.
``line_break_hyphenation``
    a hyphen at a line end may split a word between any two characters.
``possessive``
    a match may end before an apostrophe, so "Vantrell's" matches and the
    possessive stays outside the replaced span.
``initials``
    a person entry also matches by initials ("O. Vantrell", "Vantrell, O.").

A person entry declares its ``given`` and ``family`` names, because the order
of a name is not guessable ("Kiss József" puts the family name first). It
matches its full name in both orders, its initial forms and, unless the entry
says otherwise, its family name alone.

Regex classes
-------------
DOIs, grant numbers, ORCID ids, e-mail addresses, URLs and phone numbers are
matched by pattern (:data:`REGEX_PATTERNS`) on the unfolded text. Unless
``line_break_hyphenation`` is off, they also run on a view where a line
ending in a hyphen or a slash joins the next, so a wrapped URL, DOI or
address is caught whole. The dictionary says which policy category each
class falls under and what replaces it. Two patterns are narrow on purpose,
and both are declared gaps. A grant number is a nine-digit Horizon Europe
grant agreement number, spaced in threes or not. A phone number is written
in international form, starting with "+". Older grant numbers and national
phone formats need dictionary entries.

Overlaps resolve leftmost-longest. On a tie, a dictionary entry beats a
pattern, and an earlier entry beats a later one.

Constitutional standing: an authoring tool's helper. It evaluates no gate,
invokes no model and writes nothing (CLAUDE.md §13.3).
"""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from runner.anonymisation_policy import LoadedPolicy, policy_sha256
from runner.original_configuration import inside_this_repository

SCHEMA = "anonymisation_entity_dictionary/1"
RECORD_TYPE = "anonymisation_entity_dictionary"

#: Every normalisation the matcher applies, each of which can be disabled.
NORMALISATIONS: tuple[str, ...] = (
    "case",
    "diacritics",
    "whitespace",
    "line_break_hyphenation",
    "possessive",
    "initials",
)

#: An entry id is written to the edit log, so it is a code, never a name.
ENTRY_ID = re.compile(r"^[A-Z]{1,2}[0-9]{1,4}$")

#: The identifier patterns of handoff §5 A2, matched on unfolded text.
REGEX_PATTERNS: dict[str, re.Pattern[str]] = {
    "doi": re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+"),
    "grant_number": re.compile(r"(?<!\d)\d{3}(?:[ \u00a0]?\d{3}){2}(?!\d)"),
    "orcid": re.compile(r"(?<![\d-])\d{4}-\d{4}-\d{4}-\d{3}[\dX](?![\d-])"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
    "url": re.compile(r"(?:https?://|www\.)[^\s\"<>]+", re.IGNORECASE),
    "phone": re.compile(r"\+\d{1,3}(?:[ .\-]?\(?\d{1,4}\)?){2,6}"),
}

#: Punctuation that closes a sentence rather than an identifier.
_TRAILING = ".,;:)]}'\""

_ENTRY_FIELDS = ("id", "category", "surface", "variants", "replacements")
_SOFT_BREAK = r"(?:[-‐­][ \t]*\n[ \t]*)?"
_APOSTROPHES = "'’"


class DictionaryRefused(ValueError):
    """The dictionary is unreadable or malformed. The message names every problem."""


@dataclass(frozen=True)
class Person:
    given: str
    family: str
    match_family_alone: bool


@dataclass(frozen=True)
class Entry:
    id: str
    category: str
    surface: str
    variants: tuple[str, ...]
    replacements: tuple[str, ...]
    person: Optional[Person]
    #: The operator's declaration that case distinguishes this entity, such as
    #: an acronym that is also a word. Case folding is then off for the entry.
    match_case: bool
    #: ``edit``, ``flag`` or ``keep``, set by the policy (see the module docstring).
    action: str


@dataclass(frozen=True)
class RegexRule:
    regex_class: str
    category: str
    replacements: tuple[str, ...]


@dataclass(frozen=True)
class EntityDictionary:
    """A dictionary validated against one policy, with its hash."""

    record: dict[str, Any]
    sha256: str
    policy_sha256: str
    entries: tuple[Entry, ...]
    regex_rules: tuple[RegexRule, ...]


@dataclass(frozen=True)
class Match:
    """``text[start:end]`` is an occurrence. It carries no text of its own."""

    start: int
    end: int
    category: str
    entry_id: Optional[str]
    regex_class: Optional[str]
    form: str
    action: str
    replacements: tuple[str, ...]


# --------------------------------------------------------------------------- #
# The dictionary
# --------------------------------------------------------------------------- #


def dictionary_sha256(record: Mapping[str, Any]) -> str:
    """The dictionary's hash, taken like the policy's: over canonical JSON."""
    return policy_sha256(record)


def load_dictionary(path: Path, policy: LoadedPolicy) -> EntityDictionary:
    """Read and validate the dictionary at *path* against *policy*.

    The dictionary is private, so a path inside this repository is refused.
    """
    if inside_this_repository(path):
        raise DictionaryRefused(
            "the entity dictionary resolves inside this repository; it stays in the "
            "private network"
        )
    try:
        text = Path(path).read_text(encoding="utf-8")
        record = json.loads(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        # The path is private; the message names the failure, not the file.
        raise DictionaryRefused(f"the entity dictionary cannot be read: {type(exc).__name__}") from exc
    return validate_dictionary(record, policy)


def validate_dictionary(record: Any, policy: LoadedPolicy) -> EntityDictionary:
    """A validated :class:`EntityDictionary`, or :class:`DictionaryRefused` naming every problem.

    A problem names entry ids and fields, never a surface form, because the
    message may reach a log.
    """
    problems: list[str] = []
    if not isinstance(record, dict):
        raise DictionaryRefused("the entity dictionary is not a JSON object")
    if record.get("schema") != SCHEMA:
        problems.append(f"schema is not {SCHEMA}")
    if record.get("record_type") != RECORD_TYPE:
        problems.append(f"record_type is not {RECORD_TYPE}")
    categories = {c.id: c for c in policy.categories}

    entries: list[Entry] = []
    seen: set[str] = set()
    raw_entries = record.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        problems.append("entries is not a non-empty list")
        raw_entries = []
    for index, raw in enumerate(raw_entries):
        entry = _entry(raw, index, categories, seen, problems)
        if entry is not None:
            entries.append(entry)

    rules: list[RegexRule] = []
    raw_rules = record.get("regex_classes")
    if not isinstance(raw_rules, dict) or set(raw_rules) != set(REGEX_PATTERNS):
        problems.append(f"regex_classes must name exactly {sorted(REGEX_PATTERNS)}")
        raw_rules = {}
    for name in REGEX_PATTERNS:
        raw = raw_rules.get(name)
        if raw is None:
            continue
        where = f"regex class {name}"
        category = raw.get("category") if isinstance(raw, dict) else None
        if category not in categories or not categories[category].auto_edit:
            problems.append(f"{where}: category is not an auto-edited policy category")
            continue
        replacements = _replacements(raw.get("replacements"), where, problems)
        rules.append(RegexRule(name, category, replacements))

    if problems:
        raise DictionaryRefused("the entity dictionary is refused: " + "; ".join(problems))
    dictionary = EntityDictionary(
        record=copy.deepcopy(record),
        sha256=dictionary_sha256(record),
        policy_sha256=policy.sha256,
        entries=tuple(entries),
        regex_rules=tuple(rules),
    )
    _refuse_identifying_replacements(dictionary)
    return dictionary


def _entry(
    raw: Any,
    index: int,
    categories: Mapping[str, Any],
    seen: set[str],
    problems: list[str],
) -> Optional[Entry]:
    where = f"entry {index}"
    if not isinstance(raw, dict):
        problems.append(f"{where}: not an object")
        return None
    missing = [f for f in _ENTRY_FIELDS if f not in raw]
    if missing:
        problems.append(f"{where}: missing {', '.join(missing)}")
        return None
    entry_id = raw["id"]
    if not (isinstance(entry_id, str) and ENTRY_ID.match(entry_id)):
        problems.append(f"{where}: id is not a code such as E01; an id is logged, so it may not carry a name")
        return None
    where = f"entry {entry_id}"
    if entry_id in seen:
        problems.append(f"{where}: id repeated")
    seen.add(entry_id)

    category = categories.get(raw["category"])
    if category is None:
        problems.append(f"{where}: category is not a policy category")
        return None
    surfaces = [raw["surface"], *(raw["variants"] if isinstance(raw["variants"], list) else [None])]
    if not all(isinstance(s, str) and s.strip() and "\n" not in s for s in surfaces):
        problems.append(f"{where}: surface and variants must be non-empty one-line strings")

    country = raw.get("country", False)
    if country not in (True, False):
        problems.append(f"{where}: country must be true or false")
    if country and category.id != "location":
        problems.append(f"{where}: only a location can be a country")
    if country and "country" not in category.retain:
        problems.append(f"{where}: the policy does not retain the country")
    action = "keep" if country else ("edit" if category.auto_edit else "flag")

    replacements: tuple[str, ...] = ()
    if action == "edit":
        replacements = _replacements(raw["replacements"], where, problems)
    elif raw["replacements"] != []:
        problems.append(f"{where}: a {action}ed entry takes no replacement")

    match_case = raw.get("match_case", False)
    if match_case not in (True, False):
        problems.append(f"{where}: match_case must be true or false")
        match_case = False

    person = None
    if raw.get("person") is not None:
        person = _person(raw["person"], where, problems)
    if person is not None and category.id != "person_name":
        problems.append(f"{where}: only a person_name entry declares a person")

    return Entry(
        id=entry_id,
        category=category.id,
        surface=raw["surface"] if isinstance(raw["surface"], str) else "",
        variants=tuple(v for v in raw["variants"] if isinstance(v, str))
        if isinstance(raw["variants"], list) else (),
        replacements=replacements,
        person=person,
        match_case=match_case,
        action=action,
    )


def _replacements(raw: Any, where: str, problems: list[str]) -> tuple[str, ...]:
    if not (isinstance(raw, list) and raw and all(isinstance(r, str) for r in raw)):
        problems.append(f"{where}: replacements must be a non-empty list of strings")
        return ()
    if any("\n" in r or "\r" in r for r in raw):
        problems.append(f"{where}: a replacement is one line")
    if "" in raw[:-1]:
        problems.append(f"{where}: an empty replacement (a removal) may only come last")
    return tuple(raw)


def _person(raw: Any, where: str, problems: list[str]) -> Optional[Person]:
    if not (
        isinstance(raw, dict)
        and isinstance(raw.get("given"), str) and raw["given"].strip()
        and isinstance(raw.get("family"), str) and raw["family"].strip()
    ):
        problems.append(f"{where}: person needs non-empty given and family names")
        return None
    alone = raw.get("match_family_alone", True)
    if alone not in (True, False):
        problems.append(f"{where}: match_family_alone must be true or false")
        alone = True
    return Person(raw["given"].strip(), raw["family"].strip(), alone)


def _refuse_identifying_replacements(dictionary: EntityDictionary) -> None:
    """A replacement that an edited entry or a pattern would match puts an identifier back."""
    offenders = []
    for owner, replacement in [
        *((e.id, r) for e in dictionary.entries for r in e.replacements),
        *((f"regex class {r.regex_class}", x) for r in dictionary.regex_rules for x in r.replacements),
    ]:
        hits = [m for m in find_matches(replacement, dictionary) if m.action == "edit"]
        if hits:
            offenders.append(f"{owner} (matches {', '.join(sorted({m.entry_id or m.regex_class or '' for m in hits}))})")
    if offenders:
        raise DictionaryRefused(
            "the entity dictionary is refused: a replacement would itself be redacted: "
            + "; ".join(sorted(set(offenders)))
        )


# --------------------------------------------------------------------------- #
# Folding and patterns
# --------------------------------------------------------------------------- #


def _fold(text: str, disabled: frozenset[str]) -> tuple[str, list[int]]:
    """*text* folded under the enabled normalisations, and each folded character's source index."""
    out: list[str] = []
    index: list[int] = []
    for i, char in enumerate(text):
        piece = char
        if "diacritics" not in disabled:
            piece = "".join(c for c in unicodedata.normalize("NFKD", piece) if not unicodedata.combining(c))
        if "case" not in disabled:
            piece = piece.casefold()
        for c in piece:
            out.append(c)
            index.append(i)
    return "".join(out), index


def _fold_form(form: str, disabled: frozenset[str]) -> str:
    return _fold(" ".join(form.split()), disabled)[0]


def _pattern(form: str, disabled: frozenset[str]) -> re.Pattern[str]:
    """The pattern for one folded surface form."""
    soft = "" if "line_break_hyphenation" in disabled else _SOFT_BREAK
    parts: list[str] = []
    for n, char in enumerate(form):
        if char == " ":
            after_period = n > 0 and form[n - 1] == "."
            if "whitespace" in disabled:
                parts.append(" ?" if after_period else " ")
            else:
                parts.append(r"\s*" if after_period else r"\s+")
            continue
        if char in "-‐":
            parts.append(re.escape(char) + ("" if "line_break_hyphenation" in disabled else r"(?:[ \t]*\n[ \t]*)?"))
            continue
        if parts and form[n - 1] not in " -‐":
            parts.append(soft)
        parts.append(re.escape(char))
    right = r"(?![^\W_])" if "possessive" not in disabled else rf"(?![^\W_]|[{_APOSTROPHES}])"
    return re.compile(r"(?<![^\W_])" + "".join(parts) + right)


def _initial(name: str) -> str:
    """J. for Jean, and J.-P. for Jean-Pierre."""
    return "-".join(f"{part[0]}." for part in name.split("-") if part)


def _initials(given: str) -> tuple[str, ...]:
    names = given.split()
    forms = [f"{names[0][0]}.", _initial(names[0]), " ".join(_initial(n) for n in names)]
    return tuple(dict.fromkeys(forms))


def _forms(entry: Entry, disabled: frozenset[str]) -> list[tuple[str, str]]:
    """``(form kind, surface form)`` for every form *entry* matches."""
    forms = [("surface", entry.surface), *(("variant", v) for v in entry.variants)]
    person = entry.person
    if person is not None:
        forms += [
            ("full_name", f"{person.given} {person.family}"),
            ("family_first", f"{person.family} {person.given}"),
        ]
        if "initials" not in disabled:
            for initials in _initials(person.given):
                forms += [
                    ("initials", f"{initials} {person.family}"),
                    ("citation", f"{person.family}, {initials}"),
                    ("citation", f"{person.family} {initials}"),
                ]
        if person.match_family_alone:
            forms.append(("family_name", person.family))
    return forms


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #


def _strip_trailing(text: str, start: int, end: int) -> int:
    while end > start and text[end - 1] in _TRAILING:
        # A closing bracket that the identifier opened stays.
        if text[end - 1] == ")" and text.count("(", start, end) >= text.count(")", start, end):
            break
        end -= 1
    return end


#: A line break between two visible characters.
_WRAP = re.compile(r"(?<=\S)([-\u2010\u00ad]?)[ \t]*\n[ \t]*(?=\S)")


def _joined(text: str) -> tuple[str, list[int]]:
    """*text* with each line that ends in a hyphen or a slash joined to the next.

    Returns the joined text and each character's source index. A wrapping
    hyphen is dropped, because a typesetter hyphenates a wrapped URL or DOI
    far more often than its owner does. The span still covers the hyphen, so
    the redaction removes it either way.
    """
    out: list[str] = []
    index: list[int] = []
    last = 0
    for m in _WRAP.finditer(text):
        if not (m.group(1) or text[m.start() - 1] == "/"):
            continue
        out.append(text[last:m.start()])
        index.extend(range(last, m.start()))
        last = m.end()
    out.append(text[last:])
    index.extend(range(last, len(text)))
    return "".join(out), index


def find_matches(
    text: str,
    dictionary: EntityDictionary,
    *,
    disabled: Iterable[str] = (),
) -> list[Match]:
    """Every non-overlapping occurrence in *text* of an edited or flagged entry, or a pattern.

    Offsets index *text*. Kept entries are not matched. *disabled* names
    normalisations from :data:`NORMALISATIONS` to switch off.
    """
    off = frozenset(disabled)
    unknown = off - set(NORMALISATIONS)
    if unknown:
        raise ValueError(f"unknown normalisation(s): {sorted(unknown)}")
    views = {flags: _fold(text, flags) for flags in (off, off | {"case"})}

    # (start, -length, priority, order) orders candidates for leftmost-longest.
    candidates: list[tuple[int, int, int, int, Match]] = []
    order = 0
    for entry in dictionary.entries:
        if entry.action == "keep":
            continue
        flags = off | {"case"} if entry.match_case else off
        folded, index = views[flags]
        seen_forms: set[str] = set()
        for kind, form in _forms(entry, flags):
            folded_form = _fold_form(form, flags)
            if folded_form in seen_forms:
                continue
            seen_forms.add(folded_form)
            for m in _pattern(folded_form, flags).finditer(folded):
                start, end = index[m.start()], index[m.end() - 1] + 1
                match = Match(start, end, entry.category, entry.id, None, kind, entry.action,
                              entry.replacements)
                candidates.append((start, start - end, 0, order, match))
                order += 1
    pattern_views = [(text, list(range(len(text))))]
    if "line_break_hyphenation" not in off:
        pattern_views.append(_joined(text))
    for rule in dictionary.regex_rules:
        for view, source in pattern_views:
            for m in REGEX_PATTERNS[rule.regex_class].finditer(view):
                view_end = _strip_trailing(view, m.start(), m.end())
                if view_end <= m.start():
                    continue
                start, end = source[m.start()], source[view_end - 1] + 1
                match = Match(start, end, rule.category, None, rule.regex_class, "pattern",
                              "edit", rule.replacements)
                candidates.append((start, start - end, 1, order, match))
                order += 1

    chosen: list[Match] = []
    last_end = -1
    for start, _, _, _, match in sorted(candidates, key=lambda c: c[:4]):
        if start >= last_end:
            chosen.append(match)
            last_end = match.end
    return chosen
