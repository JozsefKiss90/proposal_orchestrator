"""
V03 — the named PE-09 acceptance lane stays honest.

The lane is declared as data under ``harness/acceptance_lanes/`` and read by
``harness/acceptance_lane.py``, which carries no instrument name of its own.
Four things can quietly rot a declaration: an area naming a module no longer in
the tree, a module inside the audit's focused command that belongs to no area (a
silently dropped check), an exclusion the lane declares but the run never
reports, and a skip the run reports that the lane never declared. This module
asserts all four, the loader's fail-closed behaviour, and that the lane's own
documentation carries the no-calibration statement V03 requires.

Offline. It reads the declaration, the documents and the test tree, and
exercises the JUnit reader and the reconciliation on fixtures. It never runs the
lane: that is the operator's command, and its result is recorded in the V03
completion report.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from harness import acceptance_lane as lanes

REPO_ROOT = Path(__file__).resolve().parents[2]
LANE_DOC = REPO_ROOT / "harness" / "ACCEPTANCE_LANE.md"
AUDIT = REPO_ROOT / "plans" / "reports" / "MSCA_DN_Readiness_Audit_2026-10-08.md"
LEDGER = REPO_ROOT / "plans" / "msca_dn_historical_validation_tickets.md"

#: The seven coverage areas V03's first acceptance criterion names by hand.
REQUIRED_AREAS = (
    "importer",
    "profile",
    "preflight",
    "freeze",
    "comparison",
    "provenance",
    "isolation",
)


@pytest.fixture(scope="module")
def lane() -> lanes.Lane:
    return lanes.load_lane(lanes.default_lane_path(REPO_ROOT), REPO_ROOT)


@pytest.fixture(scope="module")
def dispositions(lane: lanes.Lane) -> str:
    return (REPO_ROOT / lane.exclusion_document).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# The loader
# --------------------------------------------------------------------------- #


class TestTheLoader:
    def test_exactly_one_declaration_is_in_the_tree(self) -> None:
        """With several, the command must be told which; with none, it refuses."""
        assert len(lanes.lane_paths(REPO_ROOT)) == 1

    def test_the_reader_carries_no_instrument_name(self) -> None:
        """``tests/harness/test_profile.py`` lints this over all of ``harness``.
        Asserted here too, because the lane is the module most tempted to break
        it: its subject is one instrument's acceptance run."""
        banned = re.compile(r"msca|postdoctoral|cofund|european fellowship", re.IGNORECASE)
        for module in ("harness/acceptance_lane.py", "harness/commands/acceptance_lane.py"):
            body = (REPO_ROOT / module).read_text(encoding="utf-8")
            assert not banned.search(body), f"{module} names an instrument"

    def test_a_declaration_with_the_wrong_schema_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "x.json"
        path.write_text(json.dumps({"schema": "something/else"}), encoding="utf-8")
        with pytest.raises(ValueError, match="schema"):
            lanes.load_lane(path, tmp_path)

    def test_a_declaration_missing_a_field_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "x.json"
        path.write_text(json.dumps({"schema": lanes.SCHEMA, "lane_name": "n"}), encoding="utf-8")
        with pytest.raises(ValueError, match="the declaration has no 'areas'"):
            lanes.load_lane(path, tmp_path)

    def test_no_declaration_is_refused_rather_than_defaulted(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            lanes.default_lane_path(tmp_path)

    def test_several_declarations_refuse_to_pick_one(self, tmp_path: Path) -> None:
        directory = tmp_path / lanes.LANES_DIR_REL
        directory.mkdir(parents=True)
        (directory / "a.json").write_text("{}", encoding="utf-8")
        (directory / "b.json").write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match="name one"):
            lanes.default_lane_path(tmp_path)

    def test_a_named_lane_that_does_not_exist_names_what_does(self) -> None:
        with pytest.raises(FileNotFoundError, match="available"):
            lanes.resolve_lane_path("no-such-lane", REPO_ROOT)


# --------------------------------------------------------------------------- #
# The areas
# --------------------------------------------------------------------------- #


class TestAreas:
    def test_the_lane_has_a_name_and_a_command(self, lane: lanes.Lane) -> None:
        assert lane.name
        assert lane.command.startswith("py -3.10 -m harness.commands.acceptance_lane")

    def test_every_area_v03_names_is_declared(self, lane: lanes.Lane) -> None:
        declared = {a.name for a in lane.areas}
        for name in REQUIRED_AREAS:
            assert name in declared, f"V03 names {name!r}; the lane declares no such area"

    def test_every_area_states_an_invariant_and_names_modules(self, lane: lanes.Lane) -> None:
        for area in lane.areas:
            assert area.invariant.strip(), area.name
            assert area.modules, area.name

    def test_exactly_the_areas_v03_names_are_the_depended_on_ones(self, lane: lanes.Lane) -> None:
        """The flag is what makes criterion 2's second half measurable, so it
        must track V03's own list rather than drift from it."""
        assert {a.name for a in lane.areas if a.depended_on} == set(REQUIRED_AREAS)

    def test_every_area_module_is_in_the_tree(self, lane: lanes.Lane) -> None:
        missing = lane.modules_missing_from_disk(REPO_ROOT)
        assert missing == (), f"the lane names modules that are not in the tree: {missing}"

    def test_no_module_belongs_to_two_areas(self, lane: lanes.Lane) -> None:
        seen: dict[str, str] = {}
        for area in lane.areas:
            for module in area.modules:
                assert module not in seen, f"{module} is in both {seen[module]} and {area.name}"
                seen[module] = area.name

    def test_the_lane_covers_every_module_of_the_audits_focused_command(
        self, lane: lanes.Lane
    ) -> None:
        """A module inside the audit's command and outside every area is a
        check the lane would silently drop."""
        unassigned = lane.unassigned_focused_modules(REPO_ROOT)
        assert unassigned == (), (
            f"inside the audit's focused command, outside every area: {unassigned}"
        )

    def test_the_lane_is_a_superset_and_names_what_it_adds(self, lane: lanes.Lane) -> None:
        focused = set(lane.audit_focused_modules(REPO_ROOT))
        extras = set(lane.modules()) - focused
        assert extras == set(lane.modules_added)
        for module, why in lane.modules_added.items():
            assert why.strip(), module

    def test_every_module_left_out_is_named_with_its_reason(self, lane: lanes.Lane) -> None:
        """A module kept out of the lane is a decision, so it is stated and
        printed rather than simply absent."""
        assert lane.modules_left_out
        for module, why in lane.modules_left_out.items():
            assert (REPO_ROOT / module).is_file(), module
            assert why.strip(), module
            assert module not in lane.modules(), module

    def test_this_module_is_itself_in_the_lane(self, lane: lanes.Lane) -> None:
        assert "tests/harness/test_acceptance_lane.py" in lane.modules()


# --------------------------------------------------------------------------- #
# The audit baseline
# --------------------------------------------------------------------------- #


class TestAuditBaseline:
    def test_the_baseline_constants_are_the_audits_own_figures(self, lane: lanes.Lane) -> None:
        """The reconciliation is against a measured number, not a remembered one."""
        text = AUDIT.read_text(encoding="utf-8")
        b = lane.audit_baseline
        assert (
            f"**{b.passed:,} passed, {b.failed} failed, {b.errors} errors and {b.skipped} skipped**"
            in text
        )
        assert f"{b.collected:,} collected cases" in text

    def test_the_baseline_names_the_commit_it_was_measured_at(self, lane: lanes.Lane) -> None:
        assert lane.audit_baseline.commit in AUDIT.read_text(encoding="utf-8")

    def test_the_baseline_arithmetic_closes(self, lane: lanes.Lane) -> None:
        b = lane.audit_baseline
        assert b.passed + b.failed + b.errors + b.skipped == b.collected


# --------------------------------------------------------------------------- #
# The exclusions
# --------------------------------------------------------------------------- #


class TestExclusions:
    def test_every_exclusion_resolves_to_a_declared_module(self, lane: lanes.Lane) -> None:
        """Resolved through the declaration, not through a hard-coded
        directory: an area may name a module outside ``tests/harness/``."""
        for exclusion in lane.exclusions:
            assert lane.area_of_exclusion(exclusion) is not None, (
                f"{exclusion.check} belongs to no declared area"
            )

    def test_every_exclusion_names_a_class_that_is_in_that_module(self, lane: lanes.Lane) -> None:
        """The first run of this lane found a row naming a class that had been
        renamed. A stale class name makes a row match nothing, so the exclusion
        reads as declared while the skip reads as undeclared."""
        for exclusion in lane.exclusions:
            basename, *rest = exclusion.check.split("::")
            if not rest or not rest[0][:1].isupper():
                continue
            module = next(m for m in lane.modules() if m.rsplit("/", 1)[-1] == basename)
            body = (REPO_ROOT / module).read_text(encoding="utf-8")
            assert f"class {rest[0]}" in body, f"{exclusion.check}: no such class in {module}"

    def test_every_exclusion_is_also_in_the_exclusion_document(self, lane: lanes.Lane) -> None:
        """One list, two readers. The lane must not grow a private exclusion.

        Measured by the same method the command runs before any test, so the
        claim that the lane fails when the two disagree holds for the command
        and not only for this module."""
        assert lane.exclusions_missing_from_their_document(REPO_ROOT) == ()

    def test_every_exclusion_carries_a_reason_and_its_lift_work(self, lane: lanes.Lane) -> None:
        for exclusion in lane.exclusions:
            assert exclusion.substrate.strip(), exclusion.check
            assert exclusion.reason.strip(), exclusion.check
            assert exclusion.lifted_by.strip(), exclusion.check

    def test_every_exclusion_names_replacement_evidence(self, lane: lanes.Lane) -> None:
        """V03 criterion 2: *each exception names its module, its reason and
        its replacement evidence*. An exception without one is an uncovered
        invariant, not an accounted-for absence."""
        for exclusion in lane.exclusions:
            evidence = exclusion.replacement_evidence.strip()
            assert evidence, exclusion.check
            assert evidence.lower() != "none", (
                f"{exclusion.check}: no replacement evidence, "
                "so criterion 2 is unmet for this row"
            )

    def test_the_declared_check_count_matches_the_measured_skip_count(
        self, lane: lanes.Lane
    ) -> None:
        assert lane.declared_check_count() == lane.declared_skips

    def test_no_exclusion_covers_a_check_the_historical_run_depends_on(
        self, lane: lanes.Lane
    ) -> None:
        """V03's second criterion, measured rather than asserted.

        Each area declares whether the run depends on its invariant, and this
        resolves every exclusion to its area. A row may also flag itself, so an
        exclusion can be marked a blocker by hand when its area is not the
        whole story."""
        assert lane.exclusions_in_depended_on_areas() == ()

    def test_an_exclusion_is_never_worded_as_a_pass(self, lane: lanes.Lane) -> None:
        """Whole word: *bypass* and *passage* are not the claim at issue."""
        for exclusion in lane.exclusions:
            assert not re.search(
                r"\bpass(es|ed|ing)?\b", exclusion.reason, re.IGNORECASE
            ), exclusion.check


# --------------------------------------------------------------------------- #
# Reading a run
# --------------------------------------------------------------------------- #


JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" errors="1" failures="1" skipped="2" tests="6" time="1.0">
<testcase classname="tests.harness.test_profile" name="test_a" time="0.1"/>
<testcase classname="tests.harness.test_profile" name="test_b" time="0.1"/>
<testcase classname="tests.harness.test_profile.TestX" name="test_c" time="0.1">
<failure message="assert 1 == 2">boom</failure></testcase>
<testcase classname="tests.harness.test_profile.TestX" name="test_d" time="0.1">
<error message="setup failed">kaboom</error></testcase>
<testcase classname="tests.harness.test_gold_set.TestSeededExcellenceTemplate" name="test_e" time="0.0">
<skipped message="EXCLUDED (not a pass): no seeded gold-set template" type="pytest.skip"/></testcase>
<testcase classname="tests.harness.test_rubric_report.TestStandingLane" name="test_f" time="0.0">
<skipped message="some other reason" type="pytest.skip"/></testcase>
</testsuite></testsuites>
"""


@pytest.fixture()
def outcome() -> lanes.Outcome:
    return lanes.parse_junit(JUNIT)


class TestParseJunit:
    def test_it_reads_the_four_counts_and_derives_passed(self, outcome: lanes.Outcome) -> None:
        assert (outcome.failed, outcome.errors, outcome.skipped, outcome.collected) == (1, 1, 2, 6)
        assert outcome.passed == 2

    def test_it_names_each_failure_as_a_module_relative_node_id(
        self, outcome: lanes.Outcome
    ) -> None:
        assert outcome.failures == (
            "test_profile.py::TestX::test_c",
            "test_profile.py::TestX::test_d",
        )

    def test_it_keeps_each_skip_with_its_reason(self, outcome: lanes.Outcome) -> None:
        assert outcome.skips[0][0] == "test_gold_set.py::TestSeededExcellenceTemplate::test_e"
        assert "no seeded gold-set template" in outcome.skips[0][1]

    def test_a_class_free_test_gets_a_two_part_node_id(self) -> None:
        assert lanes.node_id("tests.harness.test_profile", "test_a") == "test_profile.py::test_a"


# --------------------------------------------------------------------------- #
# Reconciling a run against the declaration
# --------------------------------------------------------------------------- #


class TestReconcile:
    def test_a_failure_is_unexplained(self, lane: lanes.Lane, outcome: lanes.Outcome) -> None:
        result = lanes.reconcile(outcome, lane.exclusions)
        assert result.unexplained_failures == outcome.failures
        assert not result.green

    def test_a_skip_no_exclusion_declares_is_reported(
        self, lane: lanes.Lane, outcome: lanes.Outcome
    ) -> None:
        result = lanes.reconcile(outcome, lane.exclusions)
        assert "test_rubric_report.py::TestStandingLane::test_f" in result.undeclared_skips

    def test_a_declared_skip_is_matched_by_its_class_row(
        self, lane: lanes.Lane, outcome: lanes.Outcome
    ) -> None:
        """One disposition row stands for four gold-set checks, so a row may
        name a class rather than a test."""
        result = lanes.reconcile(outcome, lane.exclusions)
        assert (
            "test_gold_set.py::TestSeededExcellenceTemplate::test_e"
            not in result.undeclared_skips
        )

    def test_a_declared_exclusion_the_run_never_reported_is_reported(
        self, lane: lanes.Lane, outcome: lanes.Outcome
    ) -> None:
        result = lanes.reconcile(outcome, lane.exclusions)
        assert len(result.declared_but_absent) == len(lane.exclusions) - 1

    def test_a_clean_run_that_reports_every_exclusion_is_green(self, lane: lanes.Lane) -> None:
        skips = tuple(
            (e.check if "::test_" in e.check else e.check + "::test_x", e.reason)
            for e in lane.exclusions
        )
        clean = lanes.Outcome(
            collected=100 + len(skips),
            failed=0,
            errors=0,
            skipped=len(skips),
            failures=(),
            skips=skips,
        )
        result = lanes.reconcile(clean, lane.exclusions)
        assert result.green, result
        assert result.unexplained_failures == ()
        assert result.undeclared_skips == ()
        assert result.declared_but_absent == ()

    def test_the_findings_name_the_exclusion_document(self, lane: lanes.Lane) -> None:
        result = lanes.Reconciliation(undeclared_skips=("test_x.py::test_y",))
        assert lane.exclusion_document in result.lines(lane.exclusion_document)[0]


# --------------------------------------------------------------------------- #
# The lane's own documentation
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def doc() -> str:
    return LANE_DOC.read_text(encoding="utf-8")


class TestLaneDocumentation:
    def test_the_declaration_points_at_this_document(self, lane: lanes.Lane) -> None:
        assert lane.documentation == "harness/ACCEPTANCE_LANE.md"

    def test_it_names_the_command(self, doc: str, lane: lanes.Lane) -> None:
        assert lane.command in doc

    def test_it_names_every_area_and_its_invariant(self, doc: str, lane: lanes.Lane) -> None:
        for area in lane.areas:
            assert area.name in doc, area.name
            assert lanes.one_line(area.invariant) in lanes.one_line(doc), area.name

    def test_it_lists_every_exclusion(self, doc: str, lane: lanes.Lane) -> None:
        for exclusion in lane.exclusions:
            assert exclusion.check in doc, exclusion.check

    def test_it_states_that_passing_is_not_calibration(self, doc: str, lane: lanes.Lane) -> None:
        """V03's fourth acceptance criterion, in the lane's own words."""
        lowered = doc.lower()
        assert lane.not_evidence_of, "the declaration states nothing a green lane is not"
        for claim in lane.not_evidence_of:
            assert claim.lower() in lowered, claim

    def test_it_reconciles_against_the_audit_baseline(self, doc: str, lane: lanes.Lane) -> None:
        b = lane.audit_baseline
        assert f"{b.passed:,}" in doc
        assert b.commit in doc

    def test_it_points_at_the_exclusion_document(self, doc: str, lane: lanes.Lane) -> None:
        assert Path(lane.exclusion_document).name in doc

    def test_it_names_the_declaration_it_documents(self, doc: str, lane: lanes.Lane) -> None:
        assert lane.source in doc

    def test_the_v01_pin_is_named(self, doc: str) -> None:
        from runner import extraction_environment as env

        assert env.PINNED_PYMUPDF in doc
        assert "V01" in doc


# --------------------------------------------------------------------------- #
# The dependency gate V03 inherits
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def ledger() -> str:
    return LEDGER.read_text(encoding="utf-8")


class TestTheDependencyGate:
    def test_the_two_open_v02_criteria_are_reconciled_in_the_ledger(self, ledger: str) -> None:
        """V03 is blocked by V02a and V02c, each of which has one open box.
        The ledger must say what happened to each, by name."""
        assert "V02a criterion 2" in ledger
        assert "V02c criterion 1" in ledger

    def test_the_provenance_wording_criterion_names_v05_as_its_owner(self, ledger: str) -> None:
        amendment = _section(ledger, "## V03 ")
        assert "V02a criterion 2" in amendment
        assert "V05" in amendment

    def test_v05_carries_the_transferred_criterion(self, ledger: str) -> None:
        """Transferred, not dropped: the receiving ticket must own it."""
        v05 = _section(ledger, "## V05 ")
        assert "Inherited from V02a criterion 2" in v05

    def test_the_absent_tier3_checklist_is_recorded_as_an_exclusion(self, ledger: str) -> None:
        amendment = _section(ledger, "## V03 ")
        assert "V02c criterion 1" in amendment
        assert "xclu" in amendment, "the scoped exclusion is not named as one"

    def test_neither_reconciled_criterion_is_checked(self, ledger: str) -> None:
        """A shared constraint: a scoped exception is not a pass, and a box is
        checked only when its closure evidence exists."""
        for ticket, fragment in (
            ("## V02a ", "the V05 provenance-derived wording"),
            ("## V02c ", "the `confirmation_checklist` contract agree"),
        ):
            items = [i for i in _checkbox_items(_section(ledger, ticket)) if fragment in i]
            assert items, (ticket, fragment)
            assert items[0].startswith("- [ ]"), items[0]

    def test_the_excluded_v02c_criterion_is_traceable_to_a_lane_exclusion(
        self, lane: lanes.Lane, dispositions: str
    ) -> None:
        """The exclusion that stands for V02c's open half must exist in both
        documents, or the criterion loses its only evidence."""
        check = (
            "test_rubric_report.py::TestStandingLane::"
            "test_real_spine_register_loads_and_is_fully_confirmed"
        )
        assert any(e.check == check for e in lane.exclusions)
        assert check in dispositions


def _section(text: str, heading: str) -> str:
    """The ledger body from *heading* up to the next ticket heading."""
    start = text.index(heading)
    nxt = text.find("\n## ", start + 1)
    return text[start : nxt if nxt != -1 else len(text)]


def _checkbox_items(section: str) -> list[str]:
    """The section's checkbox list items, each joined with its wrapped lines."""
    items: list[str] = []
    for line in section.splitlines():
        if line.lstrip().startswith("- ["):
            items.append(line.strip())
        elif items and line.startswith("      "):
            items[-1] += " " + line.strip()
        elif not line.strip():
            continue
        elif items and not line.startswith(" "):
            items.append("")  # a non-item line ends the list
    return [i for i in items if i]
