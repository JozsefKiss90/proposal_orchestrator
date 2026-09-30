"""The instance-one leakage scan.

`runner/leakage_scan.py` answers the branch's anonymity constraint: no real
organisation name, person name, place, web address, grant or project identifier
from instance one appears in Tier 3, Tier 4, Tier 5 or the vault.

Two mechanisms, because a word scan alone cannot do the job:

* a **word scan** whose noun set is *derived* from the standing agnosticism-lint
  denylist, so a noun added there is scanned from that moment;
* a **pseudonymity check** over every Tier 3 artifact that describes the project,
  which reads the real country lists out of Tier 1 and fails on a country name, a
  web address or an email.

Three properties are worth pinning, and two of them exist because a first review
found the scan reporting a false clean.

**Derivation.** ``LEAKAGE_NOUNS`` is computed, not re-typed. The partition into
identity / re-identifying / scoped-out documents *why* each noun is a leak;
derivation is what makes a future addition actually get scanned. Finding F9 of the
Tier 1 coverage report is why a scoped-out set exists at all: the denylist carries
Member State names the General Annexes enumerate verbatim.

**Reuse is not completeness.** ``PROJECT_NOUNS`` was built from instance one's
Tier 3 identity spine, which names the fellow, the host and the partners — not the
project. Its acronym was missing, so ``PROJECT_IDENTIFIERS`` carries it.

**`ok` and `clean` are different questions.** The branch holds one pre-existing
leak in a Tier 4 purge record. ``ok`` answers "no new leak" and keeps the scan
usable as a regression guard; ``clean`` answers the constraint itself. Collapsing
them is what let the earlier version report clean.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.agnosticism_lint import PROJECT_NOUNS
from runner.leakage_scan import (
    IDENTITY_NOUNS,
    KNOWN_PRE_EXISTING_LEAKS,
    LEAKAGE_NOUNS,
    PROJECT_IDENTIFIERS,
    PSEUDONYMITY_EXEMPT,
    PSEUDONYMITY_JSON_GLOBS,
    PSEUDONYMITY_TEXT_GLOBS,
    REIDENTIFYING_NOUNS,
    SCAN_GLOBS,
    SCOPED_OUT,
    LeakageError,
    iter_pseudonymity_files,
    iter_vault_roots,
    leakage_denylist,
    scan_partner_records,
    scan_text,
    scan_tree,
)
from runner.paths import find_repo_root

REPO = find_repo_root()


class TestThePartition:
    def test_every_denylisted_noun_is_classified_exactly_once(self) -> None:
        scoped = frozenset(SCOPED_OUT)
        assert IDENTITY_NOUNS | REIDENTIFYING_NOUNS | scoped == PROJECT_NOUNS
        assert not IDENTITY_NOUNS & REIDENTIFYING_NOUNS
        assert not IDENTITY_NOUNS & scoped
        assert not REIDENTIFYING_NOUNS & scoped

    def test_every_scoped_out_noun_carries_a_reason(self) -> None:
        for noun, reason in SCOPED_OUT.items():
            assert reason.strip(), f"{noun} is scoped out without a reason"

    def test_the_scanned_set_is_derived_not_re_typed(self) -> None:
        """Derivation is the guarantee: a new denylist noun is scanned at once."""
        assert LEAKAGE_NOUNS == (
            PROJECT_NOUNS - frozenset(SCOPED_OUT)
        ) | PROJECT_IDENTIFIERS
        assert LEAKAGE_NOUNS == IDENTITY_NOUNS | REIDENTIFYING_NOUNS | (
            PROJECT_IDENTIFIERS
        )
        assert LEAKAGE_NOUNS

    def test_the_project_identifier_the_denylist_never_held_is_scanned(self) -> None:
        """The gap the first review found: PROJECT_NOUNS was built from instance
        one's identity spine, which names people and partners, not the project."""
        assert PROJECT_IDENTIFIERS
        assert not PROJECT_IDENTIFIERS & PROJECT_NOUNS
        assert PROJECT_IDENTIFIERS <= LEAKAGE_NOUNS

    def test_no_scoped_out_noun_is_scanned(self) -> None:
        assert not LEAKAGE_NOUNS & frozenset(SCOPED_OUT)

    def test_the_member_state_names_are_the_scoped_out_ones(self) -> None:
        """Finding F9: Tier 1 enumerates them, so Tier 4 may discuss them."""
        assert {"Hungary", "Hungarian", "Bulgaria", "Bulgarian"} <= set(SCOPED_OUT)

    def test_the_people_and_organisations_are_scanned(self) -> None:
        assert {"Cholakova", "ELTE", "AgroVIR", "Cubert"} <= IDENTITY_NOUNS


class TestTheWordScan:
    def test_it_finds_an_identity_noun(self) -> None:
        noun = sorted(IDENTITY_NOUNS)[0]
        hits = scan_text(f"the partner is {noun} and it leads WP1", leakage_denylist())
        assert [h[1] for h in hits] == [noun]

    def test_it_is_case_insensitive_and_word_bounded(self) -> None:
        hits = scan_text("elte", leakage_denylist())
        assert len(hits) == 1
        assert scan_text("Svelte components", leakage_denylist()) == []

    def test_a_scoped_out_noun_is_not_a_hit(self) -> None:
        assert scan_text("established in Hungary", leakage_denylist()) == []

    def test_an_operator_supplied_noun_is_a_hit(self) -> None:
        """The extension the ticket asks for, supplied from outside the repo."""
        denylist = leakage_denylist(extra_nouns=["Vanterra"])
        hits = scan_text("the Vanterra institute", denylist)
        assert [h[1] for h in hits] == ["Vanterra"]

    def test_it_reports_line_numbers_in_document_order(self) -> None:
        noun = sorted(IDENTITY_NOUNS)[0]
        hits = scan_text(f"a\n{noun}\nb\n{noun}", leakage_denylist())
        assert [h[0] for h in hits] == [2, 4]


class TestTheTreeScan:
    @pytest.fixture(scope="class")
    def report(self):
        return scan_tree(REPO)

    def test_no_new_leak(self, report) -> None:
        """The regression guard: nothing this branch authored carries a name."""
        assert report.ok, report.format()

    def test_the_branch_is_not_clean_and_says_so(self, report) -> None:
        """The honest answer. One pre-existing leak stands, and `clean` is False.

        `ok` and `clean` must not collapse: reporting a branch clean while a
        recorded leak stands is the false clean this separation exists to stop.
        """
        assert not report.clean
        assert report.pre_existing_violations
        assert "NOT CLEAN" in report.format()
        paths = {v.path for v in report.pre_existing_violations}
        assert paths <= set(KNOWN_PRE_EXISTING_LEAKS)

    def test_every_recorded_pre_existing_path_carries_a_reason(self) -> None:
        for path, reason in KNOWN_PRE_EXISTING_LEAKS.items():
            assert reason.strip(), f"{path} is exempted without a reason"

    def test_a_recorded_path_does_not_excuse_a_hit_elsewhere(
        self, tmp_path: Path
    ) -> None:
        """The exemption is path-scoped. The same noun elsewhere still fails."""
        recorded = tmp_path / next(iter(KNOWN_PRE_EXISTING_LEAKS))
        recorded.parent.mkdir(parents=True)
        noun = next(iter(PROJECT_IDENTIFIERS))
        recorded.write_text(f"{noun} was purged\n", encoding="utf-8")
        elsewhere = tmp_path / "docs/tier5_deliverables/draft.md"
        elsewhere.parent.mkdir(parents=True)
        elsewhere.write_text(f"building on {noun}\n", encoding="utf-8")
        report = scan_tree(tmp_path)
        assert not report.ok
        assert [v.path for v in report.new_violations] == [
            "docs/tier5_deliverables/draft.md"
        ]
        assert len(report.pre_existing_violations) == 1

    def test_it_scanned_the_tier_3_partner_records(self, report) -> None:
        assert (
            "docs/tier3_project_instantiation/consortium/partners.json"
            in report.scanned_files
        )

    def test_the_globs_cover_tiers_3_to_5_and_the_vault(self) -> None:
        joined = " ".join(SCAN_GLOBS)
        assert "tier3_project_instantiation" in joined
        assert "tier4_orchestration_state" in joined
        assert "tier5_deliverables" in joined
        assert "vault" in joined

    def test_a_planted_noun_is_caught(self, tmp_path: Path) -> None:
        target = tmp_path / "docs/tier3_project_instantiation/consortium"
        target.mkdir(parents=True)
        (target / "partners.json").write_text(
            json.dumps({"partners": [{"partner_id": "P01", "legal_name": "ELTE"}]}),
            encoding="utf-8",
        )
        report = scan_tree(tmp_path)
        assert not report.ok
        assert report.violations[0].noun == "ELTE"
        assert report.violations[0].path.endswith("partners.json")

    def test_the_report_names_file_line_and_noun(self, tmp_path: Path) -> None:
        target = tmp_path / "docs/tier5_deliverables"
        target.mkdir(parents=True)
        (target / "draft.md").write_text("line one\nJung supervises\n", encoding="utf-8")
        report = scan_tree(tmp_path)
        violation = report.violations[0]
        assert violation.line == 2
        assert violation.noun == "Jung"
        assert "draft.md:2" in report.format()


class TestVaultDiscovery:
    """A vault is found where its graph binding says it is, not where a glob guessed."""

    def test_the_generic_template_is_not_a_project_vault(self) -> None:
        roots = [r.as_posix() for r in iter_vault_roots(REPO)]
        assert not any("templates/" in r for r in roots)

    def test_a_declared_vault_path_is_discovered(self, tmp_path: Path) -> None:
        vault = tmp_path / "InstanceTwo/vault"
        vault.mkdir(parents=True)
        (tmp_path / "InstanceTwo/graph.config.yaml").write_text(
            "project_id: instance_two\nvault_path: vault\n", encoding="utf-8"
        )
        assert [r.name for r in iter_vault_roots(tmp_path)] == ["vault"]

    def test_a_noun_in_a_discovered_vault_is_caught(self, tmp_path: Path) -> None:
        vault = tmp_path / "InstanceTwo/vault/11_partners"
        vault.mkdir(parents=True)
        (tmp_path / "InstanceTwo/graph.config.yaml").write_text(
            "project_id: instance_two\nvault_path: vault\n", encoding="utf-8"
        )
        (vault / "P01.md").write_text("host: AgroVIR\n", encoding="utf-8")
        report = scan_tree(tmp_path)
        assert not report.ok
        assert report.violations[0].noun == "AgroVIR"

    def test_an_unreadable_binding_widens_the_scan(self, tmp_path: Path) -> None:
        """Scanning too much is the safe direction for a leakage check."""
        project = tmp_path / "InstanceTwo"
        project.mkdir()
        (project / "graph.config.yaml").write_text(": not yaml\n[", encoding="utf-8")
        (project / "notes.md").write_text("supervised by Jung\n", encoding="utf-8")
        report = scan_tree(tmp_path)
        assert not report.ok
        assert report.violations[0].noun == "Jung"

    def test_a_vault_path_outside_the_repository_is_ignored(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "repo/InstanceTwo"
        project.mkdir(parents=True)
        (project / "graph.config.yaml").write_text(
            "project_id: x\nvault_path: ../../elsewhere\n", encoding="utf-8"
        )
        (tmp_path / "elsewhere").mkdir()
        roots = iter_vault_roots(tmp_path / "repo")
        assert [r.name for r in roots] == ["InstanceTwo"]


class TestPseudonymityOfPartnerRecords:
    @pytest.fixture(scope="class")
    def violations(self):
        return scan_partner_records(REPO)

    def test_no_partner_record_carries_a_real_country_name(self, violations) -> None:
        assert violations == (), "\n".join(v.snippet for v in violations)

    def test_a_planted_country_name_is_caught(self, tmp_path: Path) -> None:
        self._write(tmp_path, {"partner_id": "P01", "country": "Sweden"})
        violations = scan_partner_records(tmp_path, rules_root=REPO)
        assert [v.noun for v in violations] == ["Sweden"]

    def test_a_planted_associated_country_is_caught(self, tmp_path: Path) -> None:
        self._write(tmp_path, {"partner_id": "P01", "notes": "based in Norway"})
        violations = scan_partner_records(tmp_path, rules_root=REPO)
        assert [v.noun for v in violations] == ["Norway"]

    def test_a_web_address_is_caught(self, tmp_path: Path) -> None:
        self._write(tmp_path, {"partner_id": "P01", "url": "https://example.org"})
        violations = scan_partner_records(tmp_path, rules_root=REPO)
        assert [v.noun for v in violations] == ["https://example.org"]

    def test_an_email_address_is_caught(self, tmp_path: Path) -> None:
        self._write(tmp_path, {"partner_id": "P01", "contact": "a@b.org"})
        violations = scan_partner_records(tmp_path, rules_root=REPO)
        assert [v.noun for v in violations] == ["a@b.org"]

    def test_a_country_slot_token_is_not_a_hit(self, tmp_path: Path) -> None:
        self._write(
            tmp_path, {"partner_id": "P01", "country": "C1", "country_slot": "C1"}
        )
        assert scan_partner_records(tmp_path, rules_root=REPO) == ()

    def test_an_absent_registry_is_not_a_violation(self, tmp_path: Path) -> None:
        """Nothing to scan is not a leak — it is an empty Tier 3."""
        assert scan_partner_records(tmp_path, rules_root=REPO) == ()

    def test_it_covers_every_tier_3_self_description_not_just_partners(self) -> None:
        """Country names are scoped out of the word scan, so this is the only
        mechanism that catches one. It has to reach more than one file."""
        joined = " ".join(PSEUDONYMITY_JSON_GLOBS)
        assert "consortium" in joined
        assert "working_assumptions.json" in joined
        assert "project_brief" in joined
        assert "architecture_inputs" in joined
        assert len(iter_pseudonymity_files(REPO)) >= 3

    def test_a_country_in_roles_json_is_caught(self, tmp_path: Path) -> None:
        target = tmp_path / "docs/tier3_project_instantiation/consortium"
        target.mkdir(parents=True)
        (target / "roles.json").write_text(
            json.dumps({"management_roles": [{"role": "x", "note": "based in Spain"}]}),
            encoding="utf-8",
        )
        violations = scan_partner_records(tmp_path, rules_root=REPO)
        assert [v.noun for v in violations] == ["Spain"]
        assert violations[0].path.startswith(
            "docs/tier3_project_instantiation/consortium/roles.json"
        )

    def test_a_country_in_working_assumptions_is_caught(self, tmp_path: Path) -> None:
        target = tmp_path / "docs/tier3_project_instantiation"
        target.mkdir(parents=True)
        (target / "working_assumptions.json").write_text(
            json.dumps({"declarations": [{"key": "host", "value": "Norway"}]}),
            encoding="utf-8",
        )
        assert [v.noun for v in scan_partner_records(tmp_path, rules_root=REPO)] == [
            "Norway"
        ]

    def test_the_shipped_template_is_exempt_with_a_reason(self, tmp_path: Path) -> None:
        """It declares a host country by design, to show the file's shape."""
        target = tmp_path / "docs/tier3_project_instantiation"
        target.mkdir(parents=True)
        (target / "working_assumptions.example.json").write_text(
            json.dumps({"declarations": [{"key": "host", "value": "Belgium"}]}),
            encoding="utf-8",
        )
        assert scan_partner_records(tmp_path, rules_root=REPO) == ()
        for path, reason in PSEUDONYMITY_EXEMPT.items():
            assert reason.strip(), f"{path} is exempt without a reason"

    def test_the_real_tier_3_carries_no_country_name_anywhere(self) -> None:
        violations = scan_partner_records(REPO)
        assert violations == (), "\n".join(
            f"{v.path}: [{v.kind}] {v.noun}" for v in violations
        )

    def test_an_unreadable_tier_1_fails_closed(self, tmp_path: Path) -> None:
        self._write(tmp_path, {"partner_id": "P01"})
        with pytest.raises(LeakageError):
            scan_partner_records(tmp_path, rules_root=tmp_path)

    @staticmethod
    def _write(root: Path, partner: dict) -> None:
        target = root / "docs/tier3_project_instantiation/consortium"
        target.mkdir(parents=True, exist_ok=True)
        (target / "partners.json").write_text(
            json.dumps({"partners": [partner]}), encoding="utf-8"
        )


class TestPseudonymityOfTheProseBrief:
    """The concept note and the strategic positioning are prose, not JSON.

    The word scan reads them, but country names are `SCOPED_OUT` of the word
    scan, so before this the only mechanism that catches a country never looked
    at a Markdown file. A brief is the project's own self-description, and a
    real country written into it re-identifies a derived partner exactly as a
    country written into `partners.json` does.
    """

    def test_the_text_globs_cover_the_project_brief(self) -> None:
        joined = " ".join(PSEUDONYMITY_TEXT_GLOBS)
        assert "project_brief" in joined
        assert ".md" in joined

    def test_a_country_in_the_concept_note_is_caught(self, tmp_path: Path) -> None:
        self._write(tmp_path, "concept_note.md", "The grassland sites sit in Spain.\n")
        violations = scan_partner_records(tmp_path, rules_root=REPO)
        assert [v.noun for v in violations] == ["Spain"]
        assert violations[0].kind == "country_name"

    def test_the_hit_carries_its_line_number(self, tmp_path: Path) -> None:
        """A JSON hit is located by field path and reports line 0. A prose hit
        has nowhere to point but the line, so it must carry one."""
        self._write(
            tmp_path, "concept_note.md", "First line.\n\nP07 works in Norway.\n"
        )
        violations = scan_partner_records(tmp_path, rules_root=REPO)
        assert [(v.line, v.noun) for v in violations] == [(3, "Norway")]
        assert violations[0].path.endswith("project_brief/concept_note.md")

    def test_a_web_address_in_the_positioning_note_is_caught(
        self, tmp_path: Path
    ) -> None:
        self._write(
            tmp_path, "strategic_positioning.md", "See https://example.org for P10.\n"
        )
        violations = scan_partner_records(tmp_path, rules_root=REPO)
        assert [v.noun for v in violations] == ["https://example.org"]

    def test_an_email_in_the_brief_is_caught(self, tmp_path: Path) -> None:
        self._write(tmp_path, "concept_note.md", "Write to a@b.org.\n")
        assert [v.noun for v in scan_partner_records(tmp_path, rules_root=REPO)] == [
            "a@b.org"
        ]

    def test_a_pseudonymous_brief_is_not_a_hit(self, tmp_path: Path) -> None:
        self._write(
            tmp_path,
            "concept_note.md",
            "P07 sits in country slot C3, a Member State.\n",
        )
        assert scan_partner_records(tmp_path, rules_root=REPO) == ()

    def test_an_absent_brief_is_not_a_violation(self, tmp_path: Path) -> None:
        target = tmp_path / "docs/tier3_project_instantiation/consortium"
        target.mkdir(parents=True)
        (target / "partners.json").write_text(
            json.dumps({"partners": []}), encoding="utf-8"
        )
        assert scan_partner_records(tmp_path, rules_root=REPO) == ()

    def test_the_real_brief_carries_no_country_name(self) -> None:
        violations = tuple(
            v
            for v in scan_partner_records(REPO)
            if "project_brief" in v.path
        )
        assert violations == (), "\n".join(
            f"{v.path}:{v.line}: [{v.kind}] {v.noun}" for v in violations
        )

    @staticmethod
    def _write(root: Path, name: str, text: str) -> None:
        target = root / "docs/tier3_project_instantiation/project_brief"
        target.mkdir(parents=True, exist_ok=True)
        (target / name).write_text(text, encoding="utf-8")
