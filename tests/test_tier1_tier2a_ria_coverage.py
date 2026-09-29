"""Tier 1 and Tier 2A coverage for an RIA, checked against the stored forms.

The coverage ticket in `plans/dev_graph_demo_tickets.md` asks whether the
call-neutral tiers already carry what an RIA needs, and fills what they do not
from the Tier 1 General Annexes and the Tier 2A RIA/IA forms. These checks hold
the filled artifacts to the documents they cite (CLAUDE.md §10.5, §10.6): no
rule may be written from programme knowledge, so every rule here must be a
verbatim span of the page it names.

The checks that matter most are the ones a reader cannot do by eye:

* every quote in `participation_rules.json` and in the RIA evaluator
  expectation entry occurs verbatim on the page it cites;
* the machine-readable consortium-composition numbers agree with the prose
  span they are derived from, so the consortium ticket cannot inherit a
  mis-transcribed threshold;
* the destination this project targets is checked against the General Annexes
  list of destinations exempt from the China restriction, rather than the
  restriction being applied or waived from memory;
* `runner/instrument_profile.py` still resolves an RIA profile after the
  registries are edited.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess

import pytest

from runner.instrument_profile import resolve_instrument_profile
from runner.paths import find_repo_root
from tests._tier_sources import (
    CRLF,
    LF,
    STATUSES,
    digest as _digest,
    iter_malformed_spans,
    iter_spans as _iter_spans,
    norm as _norm,
    read_pdf_pages as _read_pages,
)

REPO = find_repo_root()

TOPIC = "HORIZON-CL6-2027-01-BIODIV-01"

#: The destination this project sits in, read from the Tier 2B call extract.
DESTINATION = "Biodiversity and ecosystem services"

TIER1 = REPO / "docs/tier1_normative_framework"
GENERAL_ANNEXES = TIER1 / "programme_guidance/wp-15-general-annexes_horizon-2026-2027_en.pdf"
PARTICIPATION_RULES = TIER1 / "extracted/participation_rules.json"

TIER2A = REPO / "docs/tier2a_instrument_schemas"
AF_RIA = TIER2A / "application_forms/ria_ia/af_he-ria-ia_en.pdf"
EF_RIA = TIER2A / "evaluation_forms/ria_ia/ef_he-ria-ia_en.pdf"
INSTRUMENT_REGISTRY = TIER2A / "extracted/instrument_registry.json"
SECTION_SCHEMA_REGISTRY = TIER2A / "extracted/section_schema_registry.json"
EVALUATOR_REGISTRY = TIER2A / "extracted/evaluator_expectation_registry.json"
TEMPLATE_ADAPTER_MAP = TIER2A / "extracted/template_adapter_map.json"

CALL_EXTRACT = (
    REPO / "docs/tier2b_topic_and_call_sources/call_extracts" / (TOPIC + ".json")
)
DOCUMENT_REGISTRY = REPO / "docs/index/document_registry.json"
COVERAGE_REPORT = (
    REPO
    / "docs/tier4_orchestration_state/validation_reports"
    / "tier1-tier2a-ria-coverage_2026-09-29.json"
)
DECISION_LOG = REPO / "docs/tier4_orchestration_state/decision_log"

#: General Annexes pages the filled rules cite. Printed page == PDF page index.
GA_PAGES = (5, 6, 7, 11, 12, 13, 14, 24, 27)

#: RIA evaluation form pages the filled expectations and notes cite:
#: 2 the scoring notice, 3 the form heading, 4 and 5 the award criteria.
EF_PAGES = (2, 3, 4, 5)

#: Source spans in participation_rules.json. Pinned, not a lower bound: a
#: bound lets spans disappear from the verbatim sweep without failing it.
SPAN_COUNT = 31

#: Source spans in the coverage report, carrying the award-criteria facts.
REPORT_SPAN_COUNT = 6

#: The three award criteria of an RIA, as the evaluation form names them.
RIA_CRITERIA = (
    ("Excellence", "Excellence"),
    ("Impact", "Impact"),
    ("Implementation", "Quality and efficiency of the implementation"),
)


#: The evaluation form's running header, repeated on every page.
EF_RUNNING_HEADER = re.compile(
    r"EU Grants: Evaluation form \(HE RIA and IA\): V4\.0 . 12\.11\.2025 \d+\s*"
)


def _ef_body(pages: dict) -> str:
    """The evaluation form's body text, page furniture removed, in page order.

    One award-criterion aspect straddles the page 4/5 break: page 4 ends 'in
    the work' and page 5 opens 'programme.' behind the running header. Matching
    the aspect verbatim therefore requires joining the pages with the repeated
    header dropped. Dropping the header is normalisation of page furniture, not
    a relaxation of the match: every other character of the body is still
    required to agree with the form.
    """
    joined = " ".join(pages[page] for page in sorted(pages))
    return _norm(EF_RUNNING_HEADER.sub("", joined))


@pytest.fixture(scope="module")
def rules() -> dict:
    return json.loads(PARTICIPATION_RULES.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def evaluator_registry() -> dict:
    return json.loads(EVALUATOR_REGISTRY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def section_registry() -> dict:
    return json.loads(SECTION_SCHEMA_REGISTRY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def instrument_registry() -> dict:
    return json.loads(INSTRUMENT_REGISTRY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(COVERAGE_REPORT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ga_pages() -> dict:
    return _read_pages(GENERAL_ANNEXES, GA_PAGES)


@pytest.fixture(scope="module")
def ef_pages() -> dict:
    return _read_pages(EF_RIA, EF_PAGES)


def _ria(entries: dict) -> dict:
    """The RIA entry of a Tier 2A registry, by its declared shape."""
    matches = [
        item
        for item in entries["instruments"]
        if item.get("instrument_type") == "RIA"
    ]
    assert len(matches) == 1, "expected exactly one RIA entry, found " + str(
        len(matches)
    )
    return matches[0]


class TestStoredSources:
    def test_the_general_annexes_are_stored_under_tier_1(self) -> None:
        assert GENERAL_ANNEXES.is_file()
        assert GENERAL_ANNEXES.read_bytes()[:5] == b"%PDF-"

    def test_both_ria_forms_are_stored_under_tier_2a(self) -> None:
        for form in (AF_RIA, EF_RIA):
            assert form.is_file(), str(form)
            assert form.read_bytes()[:5] == b"%PDF-", str(form)

    def test_the_three_cited_sources_are_registered_with_a_matching_digest(
        self,
    ) -> None:
        registry = json.loads(DOCUMENT_REGISTRY.read_text(encoding="utf-8"))
        entries = {e["path"]: e for e in registry["document_registry"]}
        expected_tier = {
            GENERAL_ANNEXES: "1",
            AF_RIA: "2A",
            EF_RIA: "2A",
        }
        for source, tier in expected_tier.items():
            rel = source.relative_to(REPO).as_posix()
            assert rel in entries, rel + " is not registered"
            entry = entries[rel]
            assert entry["sha256"] == _digest(source, entry["digest_basis"]), rel
            assert entry["tier"] == tier, rel

    # The whole-registry sweep — every registered path resolves and matches its
    # digest — lives in tests/test_tier2b_biodiv_intake.py and covers the rows
    # added here too. It is not repeated: one registry checked twice per run is
    # cost without cover.

    def test_every_tier_1_and_tier_2_source_matches_the_blob_git_holds(self) -> None:
        """§13.11, checked against git's copy rather than against this ticket's own record.

        Comparing a PDF to the digest recorded beside it proves nothing: this
        ticket wrote that digest from the file as it stands, so a modified
        source would simply have been registered with its modified digest. Git
        holds an independent copy, so this hashes the committed blob of every
        source and compares it to the bytes on disk.

        What it asserts is that the working tree's sources equal the committed
        ones. It does not, and no test can, prove that some past commit never
        touched a source: that is what the history and the review are for. The
        point of running it after this ticket commits is that it stays live, and
        catches the next uncommitted edit to a source rather than going quiet.
        """
        source_trees = (
            "docs/tier1_normative_framework/legislation",
            "docs/tier1_normative_framework/programme_guidance",
            "docs/tier1_normative_framework/grant_architecture",
            "docs/tier2a_instrument_schemas/application_forms",
            "docs/tier2a_instrument_schemas/evaluation_forms",
            "docs/tier2b_topic_and_call_sources/work_programmes",
        )
        listed = subprocess.run(
            ["git", "ls-files", "-z", "--", *source_trees],
            cwd=REPO,
            capture_output=True,
        )
        assert listed.returncode == 0, (
            "git could not list the source trees, so §13.11 is unverified rather "
            "than satisfied: " + listed.stderr.decode("utf-8", "replace").strip()
        )
        tracked = [name for name in listed.stdout.decode().split(chr(0)) if name]
        assert len(tracked) >= 10, (
            "expected the Tier 1 and Tier 2 source trees to hold at least ten "
            "tracked documents, found " + str(len(tracked))
        )
        for name in tracked:
            blob = subprocess.run(
                ["git", "show", "HEAD:" + name],
                cwd=REPO,
                capture_output=True,
            )
            assert blob.returncode == 0, name + " is not in HEAD"
            on_disk = (REPO / name).read_bytes()
            committed = blob.stdout
            if not committed.startswith(b"%PDF-"):
                # core.autocrlf is true here, so a text source checks out CRLF
                # on Windows while git stores it LF. Comparing raw bytes would
                # report the platform rather than a modification. This is the
                # same rule the document registry records as digest_basis.
                committed = committed.replace(CRLF, LF)
                on_disk = on_disk.replace(CRLF, LF)
            assert hashlib.sha256(committed).hexdigest() == (
                hashlib.sha256(on_disk).hexdigest()
            ), name + " differs from the copy git holds at HEAD"

    def test_the_registered_digests_are_measured_on_the_raw_pdf_bytes(self) -> None:
        registry = json.loads(DOCUMENT_REGISTRY.read_text(encoding="utf-8"))
        entries = {e["path"]: e for e in registry["document_registry"]}
        for source in (GENERAL_ANNEXES, AF_RIA, EF_RIA):
            rel = source.relative_to(REPO).as_posix()
            assert entries[rel]["digest_basis"] == "raw_bytes", rel
            assert entries[rel]["bytes"] == source.stat().st_size, rel


class TestParticipationRulesAreVerbatim:
    def test_the_file_is_no_longer_empty(self, rules: dict) -> None:
        assert rules, "participation_rules.json is still empty"
        assert rules["schema_id"] == "tier1.participation_rules.v1"

    def test_it_names_the_general_annexes_as_its_source(self, rules: dict) -> None:
        documents = {d["document"] for d in rules["source_documents"]}
        assert GENERAL_ANNEXES.name in documents

    def test_no_object_looks_like_a_span_but_is_missing_a_key(
        self, rules: dict
    ) -> None:
        """A dropped key would remove a span from the sweep below, silently.

        `iter_spans` recognises a span only by its three keys together, so a
        renamed or mistyped key does not fail the verbatim sweep. It withdraws
        the span from the sweep and the sweep still reports green. This asserts
        there are no such near misses.
        """
        malformed = list(iter_malformed_spans(rules))
        assert not malformed, "objects missing span keys: " + str(malformed)

    def test_every_span_quotes_the_page_it_names(
        self, rules: dict, ga_pages: dict
    ) -> None:
        spans = list(_iter_spans(rules))
        assert len(spans) == SPAN_COUNT, (
            "expected " + str(SPAN_COUNT) + " spans, found " + str(len(spans))
            + ". A span that vanishes from this count is a span that stopped "
            "being checked, so the number is pinned rather than bounded."
        )
        for where, span in spans:
            page = span["source_page"]
            assert span["source_document"] == GENERAL_ANNEXES.name, where
            assert page in ga_pages, where + " cites unread page " + str(page)
            needle = _norm(span["quote"])
            assert needle, where + " quotes nothing"
            assert needle in ga_pages[page], (
                where + " is not verbatim on page " + str(page) + ": " + needle[:90]
            )

    def test_every_status_is_one_of_the_four_categories(self, rules: dict) -> None:
        statuses = rules["field_status"]
        assert statuses, "participation_rules.json carries no field_status"
        for field, status in statuses.items():
            assert status in STATUSES, field + " = " + str(status)
            assert field in rules, field + " names no field of the artifact"


class TestConsortiumComposition:
    """The condition the consortium ticket depends on."""

    def test_the_numbers_match_the_prose_they_are_derived_from(
        self, rules: dict
    ) -> None:
        composition = rules["consortium_composition"]
        assert composition["minimum_independent_beneficiaries"] == 3
        assert composition["minimum_distinct_countries"] == 3
        assert composition["minimum_in_a_member_state"] == 1
        assert composition["minimum_others_in_member_or_associated_countries"] == 2

    def test_affiliated_entities_do_not_count(self, rules: dict) -> None:
        composition = rules["consortium_composition"]
        assert composition["affiliated_entities_count_towards_the_minimum"] is False

    def test_the_deemed_established_carve_out_names_all_three_entity_kinds(
        self, rules: dict, ga_pages: dict
    ) -> None:
        composition = rules["consortium_composition"]
        deemed = composition["deemed_established_in_a_different_member_state"]
        assert set(deemed["entities"]) == {
            "Joint Research Centre",
            "international European research organisations",
            "legal entities created under EU law",
        }
        assert _norm(deemed["source_span"]["quote"]) in ga_pages[14]

    def test_the_condition_is_conditional_on_the_call(self, rules: dict) -> None:
        """'Unless otherwise provided for in the specific call/topic conditions'."""
        composition = rules["consortium_composition"]
        assert composition["overridable_by_call_conditions"] is True

    def test_the_prose_summary_does_not_drift_from_its_spans(
        self, rules: dict, ga_pages: dict
    ) -> None:
        """A correct span beside a wrong summary is the easy failure to miss.

        The spans are checked verbatim elsewhere. Nothing checks the prose
        `rule` that sits beside them, so a summary reading 'four legal
        entities' would ship green. Every claim the summary makes about the
        threshold and the limbs must also occur in the spans it summarises.
        """
        composition = rules["consortium_composition"]
        spans = " ".join(
            _norm(span["quote"]) for _, span in _iter_spans(composition)
        )
        summary = _norm(composition["rule"])
        for claim in (
            "three legal entities independent from each other",
            "established in a different country",
            "at least one",
            "Member State",
            "at least two other",
            "Member States or Associated Countries",
        ):
            assert claim in summary, "the summary drops: " + claim
            assert claim in spans, "the summary claims what no span says: " + claim
        for wrong in ("four", "two legal entities", "five"):
            assert wrong not in summary, "the summary contradicts its spans: " + wrong

    def test_the_condition_straddles_two_pages_and_says_so(
        self, rules: dict
    ) -> None:
        composition = rules["consortium_composition"]
        pages = {
            span["source_page"] for _, span in _iter_spans(composition)
        }
        assert pages == {13, 14}, (
            "the composition condition spans pages 13 and 14, not " + str(sorted(pages))
        )


class TestCountryRestrictions:
    def test_the_china_restriction_records_the_ria_rule(
        self, rules: dict, ga_pages: dict
    ) -> None:
        china = rules["country_restrictions"]["china"]
        assert china["research_and_innovation_actions"]["default"] == "not_eligible"
        assert _norm(china["research_and_innovation_actions"]["source_span"]["quote"]) in (
            ga_pages[7]
        )

    def test_this_project_destination_is_on_the_exempt_list(
        self, rules: dict
    ) -> None:
        """The restriction is resolved against the list, not from memory."""
        china = rules["country_restrictions"]["china"]
        exempt = china["research_and_innovation_actions"]["exempt_destinations"]
        assert DESTINATION in exempt

    def test_the_exempt_list_agrees_with_the_call_extract_destination(self) -> None:
        extract = json.loads(CALL_EXTRACT.read_text(encoding="utf-8"))
        assert extract["destination"] == DESTINATION

    def test_russia_belarus_and_ukraine_territories_are_recorded(
        self, rules: dict
    ) -> None:
        entry = rules["country_restrictions"]["russia_belarus_and_occupied_ukraine"]
        assert entry["eligible_in_any_capacity"] is False

    def test_the_member_state_and_associated_country_lists_are_complete(
        self, rules: dict
    ) -> None:
        funding = rules["entities_eligible_for_funding"]
        assert len(funding["member_states"]["countries"]) == 27
        assert len(funding["associated_countries"]["countries"]) == 22
        assert len(funding["overseas_countries_and_territories"]["countries"]) == 13

    def test_every_listed_country_appears_on_the_page_it_is_read_from(
        self, rules: dict, ga_pages: dict
    ) -> None:
        funding = rules["entities_eligible_for_funding"]
        for limb in (
            "member_states",
            "associated_countries",
            "overseas_countries_and_territories",
        ):
            entry = funding[limb]
            page = entry["source_span"]["source_page"]
            for country in entry["countries"]:
                assert _norm(country) in ga_pages[page], (
                    limb + ": " + country + " is not on page " + str(page)
                )

    def test_the_low_and_middle_income_limb_is_recorded_without_enumeration(
        self, rules: dict
    ) -> None:
        """Recorded as a limb with its span, and the artifact says so."""
        entry = rules["entities_eligible_for_funding"]["low_and_middle_income_countries"]
        assert "countries" not in entry
        assert entry["enumerated"] is False
        assert entry["reason"]


class TestEvaluatorExpectationsForRIA:
    def test_an_ria_entry_now_exists(self, evaluator_registry: dict) -> None:
        entry = _ria(evaluator_registry)
        ids = [c["criterion_id"] for c in entry["criteria"]]
        assert ids == [cid for cid, _ in RIA_CRITERIA]

    def test_each_criterion_carries_the_forms_threshold(
        self, evaluator_registry: dict
    ) -> None:
        for criterion in _ria(evaluator_registry)["criteria"]:
            assert criterion["threshold_score"] == 3, criterion["criterion_id"]

    def test_each_criterion_is_named_as_the_form_names_it(
        self, evaluator_registry: dict, ef_pages: dict
    ) -> None:
        names = {
            c["criterion_id"]: c["criterion_name"]
            for c in _ria(evaluator_registry)["criteria"]
        }
        body = _ef_body(ef_pages)
        for criterion_id, expected in RIA_CRITERIA:
            assert names[criterion_id] == expected
            assert _norm(expected) in body, expected

    def test_every_expectation_is_verbatim_in_the_evaluation_form(
        self, evaluator_registry: dict, ef_pages: dict
    ) -> None:
        joined = _ef_body(ef_pages)
        entry = _ria(evaluator_registry)
        for criterion in entry["criteria"]:
            expectations = criterion["evaluator_expectations"]
            assert expectations, criterion["criterion_id"] + " has no expectations"
            for text in expectations:
                assert _norm(text) in joined, (
                    criterion["criterion_id"]
                    + ": not verbatim in the evaluation form: "
                    + _norm(text)[:90]
                )

    def test_the_msca_entry_is_untouched(self, evaluator_registry: dict) -> None:
        """A regression guard: filling RIA must not disturb the other instrument."""
        msca = [
            item
            for item in evaluator_registry["instruments"]
            if item.get("instrument_type") == "MSCA-PF"
        ]
        assert len(msca) == 1
        criteria = msca[0]["criteria"]
        assert [c["criterion_id"] for c in criteria] == [
            "Excellence",
            "Impact",
            "Implementation",
        ]
        assert all(c["threshold_score"] is None for c in criteria)

    def test_the_entry_stays_inside_the_declared_schema(
        self, evaluator_registry: dict
    ) -> None:
        """§16.3: no agent introduces fields the artifact schema does not define."""
        entry = _ria(evaluator_registry)
        assert set(entry) == {"instrument_type", "criteria"}
        for criterion in entry["criteria"]:
            assert set(criterion) == {
                "criterion_id",
                "criterion_name",
                "threshold_score",
                "evaluator_expectations",
            }


class TestSectionAndInstrumentRegistries:
    def test_the_ria_section_entry_has_sections_and_a_page_limit(
        self, section_registry: dict
    ) -> None:
        entry = _ria(section_registry)
        assert entry["sections"], "RIA has no sections"
        assert isinstance(entry["part_b_page_limit_hard"], int)

    def test_the_evaluation_form_reference_now_resolves_to_a_stored_file(
        self, section_registry: dict
    ) -> None:
        entry = _ria(section_registry)
        assert entry["evaluation_form_ref"] == EF_RIA.name
        assert (TIER2A / "evaluation_forms/ria_ia" / entry["evaluation_form_ref"]).is_file()

    def test_the_evaluation_form_reference_is_no_longer_an_assumption(
        self, section_registry: dict, ef_pages: dict
    ) -> None:
        """It was Assumed from a filename convention. It is now read."""
        entry = _ria(section_registry)
        assert "evaluation_form_ref_assumption_note" not in entry
        note = entry["evaluation_form_ref_note"]
        assert "EVALUATION FORM (RIA IA)" in note
        assert "EVALUATION FORM (RIA IA)" in ef_pages[3]
        assert "V4.0" in note and "12.11.2025" in note
        assert "evaluation_form_version" not in entry, (
            "the form version belongs in the note, not in a new registry field. "
            "Decision D2 refused to add a field to the evaluator registry citing "
            "§16.3, and adding one here instead would make the pair arbitrary."
        )

    def test_the_ria_instrument_entry_agrees_with_the_topic_budget_regime(
        self, instrument_registry: dict
    ) -> None:
        entry = _ria(instrument_registry)
        extract = json.loads(CALL_EXTRACT.read_text(encoding="utf-8"))
        assert entry["budget_regime"] == extract["budget_regime"] == "lump_sum"

    def test_the_instrument_profile_still_resolves_for_ria(self) -> None:
        profile = resolve_instrument_profile(REPO, instrument_type="RIA")
        assert profile.instrument_type == "RIA"
        assert profile.budget_regime == "lump_sum"
        assert profile.hard_page_limit == 40

    def test_the_template_adapter_map_is_left_empty_on_purpose(self) -> None:
        """No schema and no consumer, so a shape here would be invented (§16.3)."""
        assert json.loads(TEMPLATE_ADAPTER_MAP.read_text(encoding="utf-8")) == {}


class TestLeakageDenylistIsNotUsableHere:
    """The consortium ticket plans a leakage scan over Tier 4 using this denylist.

    Applied to Tier 1-derived content it produces false positives, because the
    General Annexes enumerate all 27 Member States, two of which are instance
    one's countries. This pins the exact hit set and its reason, so a new noun
    turns the check red and nobody 'fixes' a Tier 1 quotation by censoring it
    (§13.11).
    """

    #: Every denylist noun that legitimately occurs in this ticket's artifacts.
    EXPECTED = {
        "Bulgaria": "a Member State in the General Annexes' own verbatim list, page 12",
        "Hungary": "a Member State in the same list, page 12",
        "Hungarian": "the Tier 1 rule on Hungarian public interest trusts, page 11",
        "MSCA": "the other instrument in this repository's registries",
        "msca": "the same, lower-cased in a path or filename",
    }

    ARTIFACTS = (
        "docs/tier1_normative_framework/extracted/participation_rules.json",
        "docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json",
        "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json",
        "docs/tier4_orchestration_state/validation_reports/"
        "tier1-tier2a-ria-coverage_2026-09-29.json",
        "docs/tier4_orchestration_state/decision_log/"
        "tier1-tier2a-ria-coverage_2026-09-29.json",
        "docs/index/document_registry.json",
    )

    def test_the_lint_does_not_claim_to_cover_docs(self) -> None:
        from runner.agnosticism_lint import GENERIC_LAYER_GLOBS

        assert not any(glob.startswith("docs/") for glob in GENERIC_LAYER_GLOBS), (
            "the agnosticism lint now covers docs/, so these artifacts are in "
            "its enforced scope and the false positives below become failures"
        )

    def test_only_the_recorded_nouns_hit(self) -> None:
        from runner.agnosticism_lint import scan_text

        found = set()
        for relative in self.ARTIFACTS:
            text = (REPO / relative).read_text(encoding="utf-8")
            found.update(noun for _, noun, _ in scan_text(text))
        unexpected = found - set(self.EXPECTED)
        assert not unexpected, (
            "a denylist noun appears that this ticket has not accounted for: "
            + str(sorted(unexpected))
        )

    def test_no_other_denylist_noun_appears_in_any_artifact(self) -> None:
        """Everything on the denylist but the five accounted-for nouns is a leak.

        The forbidden set is derived from ``PROJECT_NOUNS`` rather than restated
        here. runner/agnosticism_lint.py is the one place on this branch that
        holds the instance-one organisations, people and places, and copying
        them into a test would be the leak this check exists to catch. A first
        draft of finding F9 listed them as examples and this check turned red on
        the report, which is what the finding now records.
        """
        from runner.agnosticism_lint import PROJECT_NOUNS, scan_text

        forbidden = set(PROJECT_NOUNS) - set(self.EXPECTED)
        assert forbidden, "PROJECT_NOUNS is empty or fully allow-listed"
        for relative in self.ARTIFACTS:
            text = (REPO / relative).read_text(encoding="utf-8")
            hit = {noun for _, noun, _ in scan_text(text)} & forbidden
            assert not hit, relative + " leaks " + str(sorted(hit))


class TestCoverageReport:
    def test_the_report_covers_all_five_registries(self, report: dict) -> None:
        covered = {row["artifact"] for row in report["registry_coverage"]}
        assert covered == {
            "docs/tier1_normative_framework/extracted/participation_rules.json",
            "docs/tier2a_instrument_schemas/extracted/instrument_registry.json",
            "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json",
            "docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json",
            "docs/tier2a_instrument_schemas/extracted/template_adapter_map.json",
        }

    def test_every_row_carries_a_status_and_evidence(self, report: dict) -> None:
        for row in report["registry_coverage"]:
            artifact = row["artifact"]
            assert row["ria_entry_status"] in STATUSES, artifact
            assert (REPO / artifact).is_file(), artifact + " does not exist"
            evidence = row["evidence"]
            assert len(evidence.split()) >= 15, (
                artifact + " carries evidence too short to be evidence: " + evidence
            )
            assert row["action_taken"], artifact
            if row["ria_entry_status"] != "Confirmed":
                assert row["gap"], artifact + " is not Confirmed but names no gap"

    def test_every_finding_status_starts_with_a_declared_category(
        self, report: dict
    ) -> None:
        """§12.2 names four categories. A finding may qualify one, not replace it."""
        for finding in report["findings"]:
            status = finding["status"]
            assert any(status.startswith(name) for name in STATUSES), (
                finding["id"] + " has status " + status + ", which starts with none "
                "of the four §12.2 categories"
            )

    def test_the_page_limit_finding_names_both_limits_in_their_roles(
        self, report: dict
    ) -> None:
        """The stored limit is 40; this topic is lump sum, where 45 applies.

        Checked against the finding that owns it, not against the whole
        findings blob: page counts and byte figures elsewhere in the report
        contain both numerals, so a substring sweep would pass on nothing.
        """
        finding = self._finding(report, "F2")
        assert "40" in finding["finding"] and "45" in finding["finding"]
        assert "lump sum" in finding["finding"]
        assert "part_b_page_limit_hard" in finding["evidence"]
        assert "instrument_profile" in finding["evidence"]
        assert finding["status"] == "Unresolved"
        assert finding["not_fixed_here"]

    @staticmethod
    def _finding(report: dict, finding_id: str) -> dict:
        matches = [f for f in report["findings"] if f["id"] == finding_id]
        assert len(matches) == 1, finding_id + " is not recorded exactly once"
        return matches[0]

    def test_the_template_adapter_gap_is_recorded_as_unresolved(
        self, report: dict
    ) -> None:
        """The one criterion this ticket does not meet must read as unmet."""
        finding = self._finding(report, "F1")
        assert finding["status"] == "Unresolved"
        assert "template_adapter_map.json" in finding["finding"]
        assert finding["recommended_owner"]
        row = [
            r
            for r in report["registry_coverage"]
            if r["artifact"].endswith("template_adapter_map.json")
        ][0]
        assert row["ria_entry_status"] == "Unresolved"

    def test_every_evidence_span_in_the_report_is_verbatim(
        self, report: dict, ga_pages: dict, ef_pages: dict
    ) -> None:
        """The report carries the award-criteria facts F7 leaves unregistered.

        The RIA pre-evaluation profile ticket is told to read them from here, so
        they get the same verbatim check as the registries.
        """
        corpus = {
            GENERAL_ANNEXES.name: ga_pages,
            EF_RIA.name: ef_pages,
        }
        assert not list(iter_malformed_spans(report)), (
            "the report holds an object missing a span key, which would drop it "
            "from this sweep: " + str(list(iter_malformed_spans(report)))
        )
        spans = list(_iter_spans(report))
        assert len(spans) == REPORT_SPAN_COUNT, (
            "expected " + str(REPORT_SPAN_COUNT) + " spans, found " + str(len(spans))
        )
        for where, span in spans:
            document = span["source_document"]
            page = span["source_page"]
            assert document in corpus, where + " cites unread document " + document
            assert page in corpus[document], where + " cites unread page " + str(page)
            needle = _norm(span["quote"])
            assert needle in corpus[document][page], (
                where + " is not verbatim on " + document + " page " + str(page)
                + ": " + needle[:90]
            )

    def test_a_decision_log_entry_was_written(self) -> None:
        entry = DECISION_LOG / "tier1-tier2a-ria-coverage_2026-09-29.json"
        assert entry.is_file()
        payload = json.loads(entry.read_text(encoding="utf-8"))
        assert payload["decisions"]
