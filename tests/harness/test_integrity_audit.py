"""
The integrity audit (spec PE-07): five consistency checks over the parsed
table rows, the grounding axis enumerated Unresolved, the baseline binding.

Four groups:

* The parser over hand-built rows: wrapped header cells, repeated headers at a
  page break, continuation rows merged, the reference and month cells read.
* Each check over a small consistent world, then one planted defect per
  finding kind, each refused by name. No finding is a score, and a test pins
  that no score-shaped key appears anywhere in a report.
* The grounding axis: every claim Unresolved with the one reason, a vacuous
  ledger flagged, a ledger entry that contradicts the import contract flagged
  with its declaration visible.
* The command end to end: on the synthetic dev-graph world (document route),
  bound / re-derived / no baseline, the snapshot id unchanged after the write,
  byte-equal replay; and on the real MSCA-DN workspace, the figures the
  decision record pins.
"""
from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

import harness.commands.blind_assessment as cmd
import harness.integrity_audit as ia
from harness.blind_assessment import load_candidate
from harness.blind_baseline import (
    BASELINE_FREEZE_RECORD_TYPE,
    BASELINE_FREEZE_SCHEMA_VERSION,
)
from harness.rubrics import load_profile_bundle
from runner.atomic_write import atomic_write_json
from runner.dev_graph import build_snapshot, import_document
from runner.paths import find_repo_root
from tests.harness.test_blind_leakage import CANDIDATE, ESR_DOC, FIXTURE, FROZEN, _graph_profile

REPO = find_repo_root()
DN_WORKSPACE = REPO / "workspaces" / "msca_dn"
DN_PROFILE = REPO / "harness" / "profiles" / "msca_dn_2026_default.json"
DN_DOCUMENT = "MSCA-DN-2025_sanitised_part_b"


# --------------------------------------------------------------------------- #
# A small consistent world, built the way the importer renders one
# --------------------------------------------------------------------------- #


def _row(*cells: str) -> str:
    return "| " + " | ".join(cells) + " |"


DELIV_HEADER = _row("Numbe r", "Deliverable Title", "Short Description", "W P", "Lead Beneficiary", "Typ e", "Disseminatio n", "Due")
MILE_HEADER = _row("Number", "Title", "Related WP", "Lead Beneficiary", "Due Date", "Means of Verification")
DC_HEADER = _row("DC No.", "Recruiting Participant", "PhD Awarding Entity", "Planned Start Month", "Duration (months)",
                 "Total Duration of Secondments (months)", "Total Duration in Non- academic Sector (months)")
RISK_HEADER = _row("Description of risk", "Likelihood", "Severity", "WPs involved", "Proposed risk-mitigation measures")


def _wp_block(n: int, title: str, start: int, end: int, lead: str, dcs: str, tasks: tuple[str, ...]) -> list[str]:
    return [
        f"WP Number: {n}",
        f"WP title: {title} Start month – End month: M{start} – M{end}",
        f"Lead participant {lead}",
        "Participants Beneficiaries A, B",
        f"DCs involved {dcs}",
        "Objectives: Do the work.",
        *[f"Task {n}.{i + 1} – {t}: Text." for i, t in enumerate(tasks)],
    ]


def _dc_project(n: int, title: str, wps: str, secondments: int = 2) -> list[str]:
    return [
        f"DC{n} – {title}",
        f"Host: A university with expertise ({wps})",
        "Objectives",
        "• Do things.",
        "Key Secondments",
        *["• A partner." for _ in range(secondments)],
        "Contribution to the Network",
        "Provides a foundation.",
    ]


def consistent_world() -> dict[str, list[str]]:
    """Paragraph lists per sub-section: S1/1.1 carries DC projects, S3/3.1 the plan."""
    s11 = [
        "Intro paragraph with no claim.",
        *_dc_project(1, "First project", "WP1, WP2"),
        *_dc_project(2, "Second project", "WP2"),
        "Pertinence of the programme",
    ]
    s31 = [
        *_wp_block(1, "Methods", 1, 24, "Beneficiary A", "1", ("Analysis", "Design")),
        *_wp_block(2, "Validation", 6, 36, "Beneficiary B", "1,2", ("Trials",)),
        "Table 3.1 b Deliverables List",
        DELIV_HEADER,
        _row("D1.1", "Report", "A report", "1", "Beneficiary A", "R", "PU", "M12"),
        _row("D1.2", "Framework", "A framework", "1", "Beneficiary A", "PDE", "PU", "M24"),
        DELIV_HEADER,
        _row("D2.1", "Trial results", "Results of", "2", "Beneficiary B", "R", "PU", "M18, M36"),
        _row("", "", "the trials.", "", "", "", "", ""),
        "Table 3.1 c Milestones List",
        MILE_HEADER,
        _row("M1.1", "Framework ready", "1", "Beneficiary A", "M24", "D1.2 delivered"),
        _row("M2.1", "Trials complete", "2", "Beneficiary B", "M36", "D2.1 delivered"),
        "Table 3.1 d DC Table",
        DC_HEADER,
        _row("DC1", "Beneficiary A", "Beneficiary A", "M1", "24", "4", "2"),
        _row("DC2", "Beneficiary B", "Beneficiary B", "M6", "30", "6", "3"),
        "Table 3.1 e Project Risks",
        RISK_HEADER,
        _row("Recruitment delay", "Medium", "Medium", "1–2", "Draw from the reserve pool of applications if fewer than 3 candidates after 60% of the period."),
        _row("Data access delayed", "Low", "High", "All WPs", "Use public datasets"),
        "Recruitment risks will be mitigated through the reserve pool of applications held by the coordinator.",
    ]
    return {"S1": s11, "S2": ["Impact prose."], "S3": s31}


def _claims(section_id: str, n: int, status: str = "unresolved", source_ref: str = "") -> list[dict]:
    return [
        {"claim_id": f"{section_id}-c{i + 1:03d}", "claim_summary": f"Claim {i + 1} of {section_id}.",
         "status": status, "source_ref": source_ref, "approval": "not_applicable"}
        for i in range(n)
    ]


def write_candidate(root: Path, world: dict[str, list[str]], *, claims: dict[str, list[dict]] | None = None) -> Path:
    """Materialise *world* as section artifacts the way the blind lane does."""
    cand = root / "candidate"
    cand.mkdir(parents=True, exist_ok=True)
    sub_ids = {"S1": "1.1", "S2": "2.1", "S3": "3.1"}
    for sid, paras in world.items():
        ledger = (claims or {}).get(sid, _claims(sid, 2))
        artifact = {
            "section_id": sid,
            "document": "CAND-X@0000",
            "sub_sections": [{"sub_section_id": sub_ids[sid], "title": sid, "content": "\n\n".join(paras)}],
            "validation_status": {"claim_statuses": ledger},
        }
        atomic_write_json(artifact, cand / f"{sid}.json")
    return cand


@pytest.fixture
def profile(tmp_path: Path):
    return load_profile_bundle(_graph_profile(tmp_path), repo_root=tmp_path)


def _audit(tmp_path: Path, profile, world, **kw) -> ia.IntegrityAuditReport:
    cand = write_candidate(tmp_path, world, claims=kw.pop("claims", None))
    candidate = load_candidate(cand, profile.profile)
    return ia.run_audit(candidate, profile_id=profile.profile_id, profile_version=profile.version,
                        candidate_path=cand.as_posix(), clock=lambda: FROZEN, **kw)


def _findings(report: ia.IntegrityAuditReport, check_id: str) -> list[ia.Finding]:
    (c,) = [c for c in report.checks if c.check_id == check_id]
    return list(c.findings)


# --------------------------------------------------------------------------- #
# The parser
# --------------------------------------------------------------------------- #


class TestParser:
    def test_headers_rows_and_continuations(self, tmp_path, profile):
        report = _audit(tmp_path, profile, consistent_world())
        parse = report.parse
        assert parse["rows_rendered"] == 15
        assert parse["rows_parsed"] == 15
        assert parse["rows_merged"] == 1
        assert {k: v["rows"] for k, v in parse["tables"].items()} == {
            "deliverables": 3, "milestones": 2, "dcs": 2, "risks": 2,
        }
        assert parse["tables"]["deliverables"]["columns"][0] == "Numbe r"
        assert len(parse["wp_blocks"]) == 2 and len(parse["dc_projects"]) == 2
        assert parse["unparsed"] == []

    def test_a_continuation_row_is_merged_into_its_entry(self, tmp_path, profile):
        cand = write_candidate(tmp_path, consistent_world())
        parsed = ia.parse_candidate(load_candidate(cand, profile.profile))
        (d21,) = [r for r in parsed.table(ia.TABLE_DELIVERABLES) if r.cells[0] == "D2.1"]
        assert d21.cells[2] == "Results of the trials."
        assert len(d21.where) == 2

    def test_wp_block_fields(self, tmp_path, profile):
        cand = write_candidate(tmp_path, consistent_world())
        parsed = ia.parse_candidate(load_candidate(cand, profile.profile))
        wp2 = parsed.wp(2)
        assert wp2 is not None
        assert (wp2.start, wp2.end, wp2.lead, wp2.dcs) == (6, 36, "Beneficiary B", (1, 2))
        assert wp2.tasks == ((2, 1),)
        assert parsed.wp(1).tasks == ((1, 1), (1, 2))

    def test_dc_projects_host_wps_and_secondments(self, tmp_path, profile):
        cand = write_candidate(tmp_path, consistent_world())
        parsed = ia.parse_candidate(load_candidate(cand, profile.profile))
        assert [(p.number, p.host_wps, p.secondment_bullets) for p in parsed.dc_projects] == [
            (1, (1, 2), 2), (2, (2,), 2),
        ]

    @pytest.mark.parametrize("text, expected", [
        ("M12", ((12,), None)), ("M01", ((1,), None)), ("M12, M24, M36", ((12, 24, 36), None)),
        ("Each Beneficiary", ((), "Each Beneficiary")),
    ])
    def test_months(self, text, expected):
        assert ia._months(text) == expected

    @pytest.mark.parametrize("text, prefix, expected", [
        ("5,6", "WP", ((5, 6), None)), ("1–4", "WP", ((1, 2, 3, 4), None)), ("All WPs", "WP", (None, None)),
        ("–", "DC", ((), None)), ("DC1-9", "DC", ((1, 2, 3, 4, 5, 6, 7, 8, 9), None)),
        ("1,2,4,6,8", "DC", ((1, 2, 4, 6, 8), None)), ("", "WP", ((), None)), ("n/a", "WP", ((), None)),
        ("some text", "WP", ((), "some text")),
    ])
    def test_refs(self, text, prefix, expected):
        assert ia._refs(text, prefix=prefix) == expected

    def test_a_data_row_before_any_header_is_reported_not_dropped_silently(self, tmp_path, profile):
        world = consistent_world()
        world["S2"] = [_row("D9.9", "x", "x", "1", "x", "R", "PU", "M1")]
        report = _audit(tmp_path, profile, world)
        assert report.parse["rows_rendered"] == 16
        assert [f["kind"] for f in report.parse["unparsed"]] == [ia.KIND_UNPARSED]
        assert any(flag.startswith("parse:") for flag in report.flags)


# --------------------------------------------------------------------------- #
# The five checks
# --------------------------------------------------------------------------- #


class TestConsistentWorld:
    def test_no_findings_except_the_not_comparable_hosts(self, tmp_path, profile):
        report = _audit(tmp_path, profile, consistent_world())
        kinds = sorted({f.kind for f in report.findings})
        assert kinds == [ia.KIND_NOT_COMPARABLE], [f.to_dict() for f in report.findings]
        assert [c.check_id for c in report.checks] == [c for c, _ in ia.CHECKS]
        assert all(c.compared > 0 for c in report.checks)

    def test_risk_notes_name_the_threshold_and_the_linked_rows(self, tmp_path, profile):
        report = _audit(tmp_path, profile, consistent_world())
        (risk,) = [c for c in report.checks if c.check_id == "risk_table_vs_prose"]
        assert "threshold stated in any risk row: yes (risk 1: '60%')" in risk.notes
        assert any("risk rows they link to: [0]" in n for n in risk.notes)


class TestCheckWorkPackages:
    def test_missing_lead_and_dcs_are_named(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p for p in world["S3"] if p not in ("Lead participant Beneficiary A", "DCs involved 1")]
        f = _findings(_audit(tmp_path, profile, world), "wp_table_vs_prose")
        missing = {(x.subject, x.detail) for x in f if x.kind == ia.KIND_MISSING_FIELD}
        assert ("WP1", "WP1 declares no lead participant") in missing
        assert ("WP1", "WP1 declares no DCs involved") in missing

    def test_dcs_involved_against_the_dc_projects(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("DCs involved 1,2", "DCs involved 2") for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "wp_table_vs_prose")
        (x,) = [x for x in f if x.kind == ia.KIND_INCONSISTENCY]
        assert x.subject == "WP2"
        assert x.context == {"declared": [2], "from_dc_projects": [1, 2]}

    def test_a_task_under_the_wrong_package(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("Task 2.1 –", "Task 3.1 –") for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "wp_table_vs_prose")
        assert [x.detail for x in f if x.kind == ia.KIND_INCONSISTENCY] == ["Task 3.1 is described under WP2"]

    def test_a_referenced_but_undescribed_package(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace('"2", "Beneficiary B", "R", "PU", "M18, M36"', "") for p in world["S3"]]
        world["S3"] = [p.replace("| D2.1 | Trial results | Results of | 2 |", "| D2.1 | Trial results | Results of | 9 |") for p in world["S3"]]
        report = _audit(tmp_path, profile, world)
        wp = _findings(report, "wp_table_vs_prose")
        assert any(x.subject == "WP9" and x.kind == ia.KIND_MISSING_FIELD for x in wp)
        deliv = _findings(report, "deliverable_wp_window")
        assert [x.detail for x in deliv] == ["D2.1 belongs to WP9, which no work-package block describes"]


class TestCheckDeliverables:
    def test_a_deliverable_outside_its_window(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace('| D1.2 | Framework | A framework | 1 | Beneficiary A | PDE | PU | M24 |',
                                 '| D1.2 | Framework | A framework | 1 | Beneficiary A | PDE | PU | M30 |') for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "deliverable_wp_window")
        (x,) = f
        assert (x.kind, x.subject, x.detail) == (ia.KIND_OUT_OF_WINDOW, "D1.2", "D1.2 is due M30; WP1 runs M1-M24")
        assert x.context == {"month": 30, "window": [1, 24]}
        assert len(x.where) == 2  # the row and the block

    def test_a_due_cell_that_does_not_parse(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("| PU | M12 |", "| PU | TBD |") for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "deliverable_wp_window")
        assert [(x.kind, x.subject) for x in f] == [(ia.KIND_UNPARSED, "D1.1")]

    def test_a_duplicate_id(self, tmp_path, profile):
        world = consistent_world()
        world["S3"].insert(world["S3"].index(DELIV_HEADER) + 2,
                           _row("D1.1", "Again", "x", "1", "Beneficiary A", "R", "PU", "M12"))
        f = _findings(_audit(tmp_path, profile, world), "deliverable_wp_window")
        assert [x.detail for x in f] == ["D1.1 appears twice"]


class TestCheckMilestones:
    def test_a_milestone_before_the_deliverable_it_depends_on(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("| M1.1 | Framework ready | 1 | Beneficiary A | M24 |",
                                 "| M1.1 | Framework ready | 1 | Beneficiary A | M20 |") for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "milestone_dependencies")
        (x,) = f
        assert (x.kind, x.detail) == (ia.KIND_INCONSISTENCY, "M1.1 is due M20 but depends on D1.2, due M24")
        assert x.context == {"milestone_month": 20, "deliverable_months": [24]}

    def test_a_named_deliverable_the_table_does_not_list(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("D1.2 delivered", "D1.7 delivered") for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "milestone_dependencies")
        assert [x.detail for x in f] == ["M1.1 names D1.7, which the deliverables table does not list"]

    def test_an_undeclared_dependency_is_context_not_failure(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("D1.2 delivered", "Framework in the repository") for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "milestone_dependencies")
        (x,) = f
        assert x.kind == ia.KIND_UNDECLARED
        assert x.context == {
            "related_wps": [1],
            "deliverables_of_related_wps": [{"id": "D1.1", "months": [12]}, {"id": "D1.2", "months": [24]}],
        }
        assert "not judged" in x.detail

    def test_a_milestone_outside_its_related_window(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("| M2.1 | Trials complete | 2 | Beneficiary B | M36 |",
                                 "| M2.1 | Trials complete | 2 | Beneficiary B | M48 |") for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "milestone_dependencies")
        assert [x.detail for x in f if x.kind == ia.KIND_OUT_OF_WINDOW] == [
            "M2.1 is due M48; its related WP2 runs M6-M36"
        ]


class TestCheckDcs:
    def test_the_dc_set_must_agree(self, tmp_path, profile):
        world = consistent_world()
        world["S1"] = [p for p in world["S1"] if "DC2" not in p]
        # drop DC2's whole project block
        world["S1"] = world["S1"][: world["S1"].index("Pertinence of the programme") - 7] + ["Pertinence of the programme"]
        f = _findings(_audit(tmp_path, profile, world), "dc_table_vs_projects")
        (x,) = [x for x in f if x.subject == "DC set"]
        assert x.context == {"table": [1, 2], "projects": [1]}

    def test_a_contract_running_past_its_packages(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("| DC1 | Beneficiary A | Beneficiary A | M1 | 24 |",
                                 "| DC1 | Beneficiary A | Beneficiary A | M6 | 36 |") for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "dc_table_vs_projects")
        (x,) = [x for x in f if x.kind == ia.KIND_OUT_OF_WINDOW]
        assert x.detail == "DC1 runs M6-M41 (36 months); WP1 ends M24, WP2 ends M36"
        assert x.context == {"dc_window": [6, 41], "wps_ending_before": [[1, 24], [2, 36]]}

    def test_secondments_longer_than_the_contract(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("| M6 | 30 | 6 | 3 |", "| M6 | 30 | 31 | 3 |") for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "dc_table_vs_projects")
        assert [x.detail for x in f if x.kind == ia.KIND_INCONSISTENCY] == [
            "DC2: 31 secondment months exceed the 30-month contract"
        ]

    def test_the_host_is_reported_not_comparable_with_both_values(self, tmp_path, profile):
        f = _findings(_audit(tmp_path, profile, consistent_world()), "dc_table_vs_projects")
        (x,) = [x for x in f if x.subject == "DC1" and x.kind == ia.KIND_NOT_COMPARABLE]
        assert x.context == {"recruiting_participant": "Beneficiary A",
                             "host_line": "A university with expertise (WP1, WP2)"}


class TestCheckRisks:
    def test_no_threshold_is_said_in_those_words(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("if fewer than 3 candidates after 60% of the period", "as needed") for p in world["S3"]]
        (risk,) = [c for c in _audit(tmp_path, profile, world).checks if c.check_id == "risk_table_vs_prose"]
        assert "threshold stated in any risk row: no" in risk.notes

    def test_an_empty_mitigation_cell(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("| All WPs | Use public datasets |", "| All WPs |  |") for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "risk_table_vs_prose")
        assert [x.detail for x in f] == ["risk 2 states no mitigation measure"]

    def test_a_prose_mitigation_no_row_carries(self, tmp_path, profile):
        world = consistent_world()
        world["S2"] = ["Vendor lock-in risks will be mitigated through open interfaces and escrowed firmware."]
        f = _findings(_audit(tmp_path, profile, world), "risk_table_vs_prose")
        (x,) = f
        assert x.kind == ia.KIND_UNLINKED_PROSE and x.where[0].sub_section_id == "2.1"

    def test_a_mitigation_naming_an_undescribed_package(self, tmp_path, profile):
        world = consistent_world()
        world["S3"] = [p.replace("| Medium | Medium | 1–2 |", "| Medium | Medium | 1–3 |") for p in world["S3"]]
        f = _findings(_audit(tmp_path, profile, world), "risk_table_vs_prose")
        assert [x.detail for x in f] == ["risk 1 involves WP3, which no work-package block describes"]


# --------------------------------------------------------------------------- #
# No finding is a score
# --------------------------------------------------------------------------- #


def _keys(obj, acc: set[str]) -> set[str]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(str(k))
            _keys(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _keys(v, acc)
    return acc


class TestNoScore:
    def test_no_score_shaped_key_anywhere(self, tmp_path, profile):
        data = _audit(tmp_path, profile, consistent_world()).to_dict()
        keys = _keys(data, set())
        forbidden = {k for k in keys if any(w in k.lower() for w in ("score", "grade", "passed", "verdict", "rate", "threshold_met"))}
        assert not forbidden, forbidden
        assert data["advisory"] is True and data["blocking"] is False
        assert "no finding is a proposal-quality score" in data["notes"]

    def test_every_finding_kind_is_enumerated(self):
        with pytest.raises(ValueError):
            ia.Finding("c", "severity", "x", "y")


# --------------------------------------------------------------------------- #
# The grounding axis
# --------------------------------------------------------------------------- #


class TestGrounding:
    def test_every_claim_is_unresolved_for_the_one_reason(self, tmp_path, profile):
        g = _audit(tmp_path, profile, consistent_world()).grounding
        assert g["claims_total"] == 6 and g["unresolved"] == 6 and g["vacuous"] is False
        assert g["judge"] is None and g["flags"] == []
        assert {r["status"] for r in g["rows"]} == {ia.GROUNDING_STATUS}
        assert {r["severity"] for r in g["rows"]} == {"unresolved"}
        assert {r["reason"] for r in g["rows"]} == {ia.GROUNDING_REASON}
        assert ia.GROUNDING_REASON == "supporting sources removed by sanitisation"

    def test_a_vacuous_ledger_is_flagged(self, tmp_path, profile):
        report = _audit(tmp_path, profile, consistent_world(), claims={"S1": [], "S2": [], "S3": []})
        assert report.grounding["vacuous"] is True and report.grounding["claims_total"] == 0
        assert any("vacuous" in f for f in report.flags)

    def test_a_declaration_other_than_unresolved_is_flagged_and_still_unresolved(self, tmp_path, profile):
        report = _audit(tmp_path, profile, consistent_world(),
                        claims={"S1": _claims("S1", 1, status="confirmed", source_ref="docs/x.json")})
        (row,) = [r for r in report.grounding["rows"] if r["section_id"] == "S1"]
        assert row["declared_status"] == "confirmed" and row["status"] == "Unresolved"
        assert row["assertion_location"] == "docs/x.json"
        assert [f for f in report.flags if "declares status 'confirmed'" in f]

    def test_a_section_without_a_ledger_array_is_a_flag_not_a_crash(self, tmp_path, profile):
        cand = write_candidate(tmp_path, consistent_world())
        data = json.loads((cand / "S2.json").read_text(encoding="utf-8"))
        del data["validation_status"]
        atomic_write_json(data, cand / "S2.json")
        candidate = load_candidate(cand, profile.profile)
        g = ia.enumerate_grounding(candidate)
        assert g["claims_total"] == 4 and any(f.startswith("S2:") for f in g["flags"])


# --------------------------------------------------------------------------- #
# The baseline binding
# --------------------------------------------------------------------------- #


def _freeze(baseline_dir: Path, *, candidate_hash: str, snapshot_id: str) -> None:
    """A minimal freeze the loader accepts: the copy's hash must match the record."""
    baseline_dir.mkdir(parents=True, exist_ok=True)
    copy = baseline_dir / "blind_baseline_000000000000.json"
    copy.write_bytes(b'{"record_type": "blind_assessment_report"}')
    import hashlib

    record = {
        "record_type": BASELINE_FREEZE_RECORD_TYPE,
        "schema_version": BASELINE_FREEZE_SCHEMA_VERSION,
        "advisory": True, "blocking": False,
        "report_copy": copy.name,
        "report_sha256": hashlib.sha256(copy.read_bytes()).hexdigest(),
        "bindings": {"candidate_hash": candidate_hash, "snapshot_id": snapshot_id},
    }
    atomic_write_json(record, baseline_dir / "blind_baseline_000000000000.freeze.json")


class TestBaseline:
    def test_no_directory_means_none_consulted(self):
        b = ia.bind_baseline(None, candidate_digest="sha256:a", snapshot_id="sha256:s")
        assert b["status"] == ia.BASELINE_NONE and "no frozen baseline was consulted" in b["statement"]

    def test_bound_when_both_ids_agree(self, tmp_path):
        _freeze(tmp_path / "b", candidate_hash="sha256:a", snapshot_id="sha256:s")
        b = ia.bind_baseline(tmp_path / "b", candidate_digest="sha256:a", snapshot_id="sha256:s")
        assert b["status"] == ia.BASELINE_BOUND

    def test_rederived_when_the_snapshot_moved(self, tmp_path):
        _freeze(tmp_path / "b", candidate_hash="sha256:a", snapshot_id="sha256:s")
        b = ia.bind_baseline(tmp_path / "b", candidate_digest="sha256:a", snapshot_id="sha256:t")
        assert b["status"] == ia.BASELINE_REDERIVED
        assert "re-derived" in b["statement"] and "sha256:s" in b["statement"] and "sha256:t" in b["statement"]

    def test_another_candidate_is_said(self, tmp_path):
        _freeze(tmp_path / "b", candidate_hash="sha256:a", snapshot_id="sha256:s")
        b = ia.bind_baseline(tmp_path / "b", candidate_digest="sha256:z", snapshot_id="sha256:s")
        assert b["status"] == ia.BASELINE_OTHER_CANDIDATE

    def test_directory_route_cannot_rederive_the_snapshot(self, tmp_path):
        _freeze(tmp_path / "b", candidate_hash="sha256:a", snapshot_id="sha256:s")
        b = ia.bind_baseline(tmp_path / "b", candidate_digest="sha256:a", snapshot_id="")
        assert b["status"] == ia.BASELINE_UNKNOWN_SNAPSHOT

    def test_a_directory_without_a_freeze_is_refused(self, tmp_path):
        with pytest.raises(ia.IntegrityAuditError):
            ia.bind_baseline(tmp_path / "empty", candidate_digest="sha256:a", snapshot_id="sha256:s")

    def test_rederived_and_other_candidate_are_flags(self, tmp_path, profile):
        cand = write_candidate(tmp_path, consistent_world())
        candidate = load_candidate(cand, profile.profile)
        _freeze(tmp_path / "b", candidate_hash="sha256:zzz", snapshot_id="sha256:s")
        report = ia.run_audit(candidate, profile_id="p", profile_version="v", candidate_path="c",
                              baseline_dir=tmp_path / "b", clock=lambda: FROZEN)
        assert any(f.startswith("baseline:") for f in report.flags)


# --------------------------------------------------------------------------- #
# The command on the synthetic dev-graph world
# --------------------------------------------------------------------------- #


@pytest.fixture
def world(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    import_document(root, CANDIDATE)
    import_document(root, ESR_DOC, state="submitted")
    return root


@pytest.fixture
def bundle(world: Path):
    return load_profile_bundle(_graph_profile(world), repo_root=world)


def _run(world: Path, bundle, *extra: str, out: Path | None = None) -> tuple[int, Path, dict]:
    # Reports go beside the world, never under the graph root (the audit flags that).
    out = out or (world.parent / "audits")
    code = cmd.main(
        ["audit", "--document", "CAND-1", "--graph-root", str(world), "--out-dir", str(out),
         "--repo-root", str(world), "--profile", str(bundle.profile.source_path), *extra],
        clock=lambda: FROZEN,
    )
    (path,) = [p for p in out.iterdir() if p.is_file()]
    return code, path, ia.load_audit(path)


class TestCommand:
    def test_document_route_binds_snapshot_and_leaves_it_unchanged(self, world, bundle, capsys):
        before = build_snapshot(world).snapshot_id
        code, path, data = _run(world, bundle)
        # The synthetic ledger declares confirmed and inferred claims, which an
        # imported proposal never does: flagged, so exit 1, and still Unresolved.
        assert code == 1, capsys.readouterr().out
        assert sorted(data["flags"]) == [
            "S1/CL-3#0 declares status 'inferred', not 'unresolved'; the declaration is not evidence and the claim is still reported Unresolved",
            "S2/CL-1#0 declares status 'confirmed', not 'unresolved'; the declaration is not evidence and the claim is still reported Unresolved",
            "S2/CL-2#1 declares status 'confirmed', not 'unresolved'; the declaration is not evidence and the claim is still reported Unresolved",
        ]
        assert {r["status"] for r in data["grounding"]["rows"]} == {"Unresolved"}
        assert data["evidence_source"] == "dev_graph_blind_view"
        assert data["snapshot_id"] == before == build_snapshot(world).snapshot_id
        assert data["document_id"] == "CAND-1" and data["package_id"]
        assert data["baseline"]["status"] == ia.BASELINE_NONE
        # A candidate without tables: every check ran and compared nothing, said so.
        for check in data["checks"]:
            assert check["findings_total"] == 0
        assert any("compared nothing" in n for c in data["checks"] for n in c["notes"])
        assert "(unchanged)" in capsys.readouterr().out
        assert path.name.startswith("integrity_") and data["writes"] == [(world.parent / "audits" / path.name).as_posix()]

    def test_an_out_dir_under_the_graph_root_is_flagged(self, world, bundle):
        code, _, data = _run(world, bundle, out=world / "audits")
        assert code == 1 and any(f.startswith("out-dir") and "lies under the graph root" in f for f in data["flags"])

    def test_bound_to_a_frozen_baseline(self, world, bundle):
        code, _, first = _run(world, bundle, out=world.parent / "a1")
        _freeze(world / "baseline", candidate_hash=first["candidate_hash"], snapshot_id=first["snapshot_id"])
        code, _, data = _run(world, bundle, "--baseline-dir", "baseline", out=world.parent / "a2")
        assert data["baseline"]["status"] == ia.BASELINE_BOUND
        assert not any(f.startswith("baseline:") for f in data["flags"])
        assert data["baseline"]["snapshot_id_frozen"] == data["snapshot_id"]

    def test_a_rederived_baseline_is_said_and_flagged(self, world, bundle, capsys):
        code, _, first = _run(world, bundle, out=world.parent / "a1")
        _freeze(world / "baseline", candidate_hash=first["candidate_hash"], snapshot_id="sha256:elsewhere")
        code, _, data = _run(world, bundle, "--baseline-dir", "baseline", out=world.parent / "a2")
        assert code == 1 and data["baseline"]["status"] == ia.BASELINE_REDERIVED
        assert any(f.startswith("baseline: the baseline was re-derived") for f in data["flags"])
        assert "re-derived" in capsys.readouterr().out

    def test_a_missing_baseline_directory_fails_closed(self, world, bundle, capsys):
        out = world.parent / "a"
        code = cmd.main(
            ["audit", "--document", "CAND-1", "--graph-root", str(world), "--out-dir", str(out),
             "--repo-root", str(world), "--profile", str(bundle.profile.source_path), "--baseline-dir", "nowhere"],
            clock=lambda: FROZEN,
        )
        # The evidence was materialised under the out dir before the refusal; no report was.
        assert code == 2 and not list(out.glob("integrity_*.json"))
        assert "no baseline could be read" in capsys.readouterr().err

    def test_replay_is_byte_equal(self, world, bundle):
        _, p1, _ = _run(world, bundle, out=world.parent / "a1")
        _, p2, _ = _run(world, bundle, out=world.parent / "a2")
        d1, d2 = json.loads(p1.read_text("utf-8")), json.loads(p2.read_text("utf-8"))
        # The two runs materialise into different out dirs by design; everything else is equal.
        for d in (d1, d2):
            d.pop("writes"), d.pop("candidate_path")
        assert d1 == d2

    def test_the_loader_refuses_a_report_that_is_not_advisory(self, world, bundle):
        _, path, data = _run(world, bundle)
        data = copy.deepcopy(data)
        data["blocking"] = True
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ia.IntegrityAuditError):
            ia.load_audit(path)


# --------------------------------------------------------------------------- #
# The real MSCA-DN workspace: the figures the decision record pins
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not DN_WORKSPACE.is_dir(), reason="MSCA-DN workspace not on this branch")
class TestMscaDnWorkspace:
    @pytest.fixture(scope="class")
    def report(self, tmp_path_factory) -> dict:
        out = tmp_path_factory.mktemp("dn_audit")
        code = cmd.main(
            ["audit", "--document", DN_DOCUMENT, "--graph-root", str(DN_WORKSPACE), "--out-dir", str(out),
             "--repo-root", str(REPO), "--profile", str(DN_PROFILE)],
            clock=lambda: FROZEN,
        )
        assert code == 0
        (path,) = [p for p in out.iterdir() if p.is_file()]
        return ia.load_audit(path)

    def test_parse_figures(self, report):
        parse = report["parse"]
        assert (parse["rows_rendered"], parse["rows_parsed"], parse["rows_merged"]) == (88, 88, 8)
        assert {k: v["rows"] for k, v in parse["tables"].items()} == {
            "deliverables": 28, "milestones": 16, "dcs": 9, "risks": 10,
        }
        assert len(parse["wp_blocks"]) == 7 and len(parse["dc_projects"]) == 9
        assert parse["unparsed"] == [] and report["flags"] == []

    def test_findings_by_check(self, report):
        by_check = {c["check_id"]: c["findings_by_kind"] for c in report["checks"]}
        assert by_check == {
            "wp_table_vs_prose": {"inconsistency": 4, "missing_field": 3},
            "deliverable_wp_window": {},
            "milestone_dependencies": {"undeclared_dependency": 16, "out_of_window": 1},
            "dc_table_vs_projects": {"out_of_window": 9, "not_comparable": 9},
            "risk_table_vs_prose": {},
        }

    def test_the_named_findings(self, report):
        details = {f["detail"] for c in report["checks"] for f in c["findings"]}
        assert "WP4 declares no lead participant" in details
        assert "WP4 declares no DCs involved" in details
        assert "M7.3 is due M48; its related WP7 runs M1-M36" in details
        assert "DC1 runs M5-M40 (36 months); WP1 ends M36, WP2 ends M36, WP4 ends M36" in details
        assert any(d.startswith("WP1 declares DCs involved [1, 2, 4, 6, 8]; the DC projects in 1.1 that name WP1") for d in details)
        (risk,) = [c for c in report["checks"] if c["check_id"] == "risk_table_vs_prose"]
        assert "threshold stated in any risk row: yes (risk 1: '60%')" in risk["notes"]

    def test_grounding_axis(self, report):
        g = report["grounding"]
        assert g["claims_total"] == 45 and g["unresolved"] == 45 and g["vacuous"] is False
        assert {r["status"] for r in g["rows"]} == {"Unresolved"}
        assert {r["reason"] for r in g["rows"]} == {"supporting sources removed by sanitisation"}
        assert all(r["declared_status"] == "unresolved" for r in g["rows"])

    def test_no_baseline_yet_is_said(self, report):
        assert report["baseline"]["status"] == ia.BASELINE_NONE
