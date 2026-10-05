"""
Evidence preflight (``harness.evidence_preflight``) — spec PE-05.

The preflight is the Claude-free command an operator runs before spending
assessor quota.  It realises every evidence pack the blind lane would build,
reports what each pack dropped and why, and binds the realised pack set by
hash.  ``assess`` requires that hash and refuses on mismatch.

Everything here runs offline against a call-neutral synthetic profile; the
document-route tests use the synthetic dev-graph fixture copied under
``tmp_path``.  The last class re-derives the shipped candidate's preflight
from the committed workspace, which the import tests already keep byte-stable.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import harness.blind_assessment as ba
import harness.commands.blind_assessment as cmd
import harness.evidence_preflight as pf
from harness.evidence_pack import (
    EXCLUDED_NOT_RELEVANT,
    EXCLUDED_OVER_BUDGET,
    PACK_COMPLETE,
    PACK_INSUFFICIENT_CONTEXT,
)
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import load_profile_bundle
from runner.dev_graph import build_snapshot, import_document
from runner.paths import find_repo_root

REPO = find_repo_root()
FIXTURE = REPO / "tests" / "fixtures" / "dev_graph_synthetic"
FROZEN = "2026-10-05T12:00:00+00:00"
PASS_JSON = '{"passed": true, "score": 0.9, "rationale": "scripted pass"}'
CRITERION_JSON = json.dumps(
    {"score": 4.0, "shortcomings": ["one named shortcoming"], "strengths": ["s"],
     "rationale": "scripted criterion score"}
)

RELEVANT = "The modelling objectives are original and go beyond current practice."
IRRELEVANT = "Weather on the day of the kick-off meeting was mild and dry."
ROWS = [
    "| WP | Lead | Start | End |",
    "| WP1 | Participant B | 1 | 12 |",
    "| WP2 | Participant C | 6 | 24 |",
]


def _write_json(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# A call-neutral synthetic profile: three criteria, one section each
# --------------------------------------------------------------------------- #

#: (criterion id, registry name, expectation key, aspect text, section id, anchors, terms)
CRITERIA = [
    ("novelty", "Novelty", "nov-obj", "Originality of the objectives", "novelty_section",
     ["N.1"], ["objective", "objectives", "original"]),
    ("reach", "Reach", "reach-uptake", "Breadth of the uptake", "reach_section",
     ["R.1"], ["uptake", "partner"]),
    ("feasibility", "Feasibility", "feas-plan", "Credibility of the plan", "feasibility_section",
     ["F.1", "F.2"], ["plan", "work package", "WP"]),
]


def _synthetic_profile(root: Path, *, sections=None) -> Path:
    """Write the profile bundle under *root* and return the profile path.

    *sections* overrides the criterion-to-section map (used by the document
    route, whose fixture candidate carries sections S1, S2 and S3).
    """
    section_of = sections or {cid: sid for cid, _r, _k, _t, sid, _a, _terms in CRITERIA}
    anchors_of = {cid: (a if sections is None else [section_of[cid]])
                  for cid, _r, _k, _t, _s, a, _terms in CRITERIA}
    registry = {
        "instruments": [
            {
                "instrument_type": "SYN-TRI",
                "criteria": [
                    {"criterion_id": rid, "evaluator_expectations": [text]}
                    for _c, rid, _k, text, _s, _a, _terms in CRITERIA
                ],
            }
        ]
    }
    scorecard = {
        "scorecard_id": "syn_tri_scorecard",
        "provenance": {"version": "0.1"},
        "scoring": {
            "scale": "0-5, one decimal place",
            "levels": {str(i): f"level {i}" for i in range(6)},
            "overall_threshold": 70,
            "overall_max": 100,
            "individual_threshold": 3,
        },
        "criteria": [
            {
                "id": cid,
                "name": rid,
                "weight_pct": weight,
                "aspects": [{"id": key, "text": text, "option_tag": "Track one", "source_page": 1}],
            }
            for (cid, rid, key, text, _s, _a, _terms), weight in zip(CRITERIA, (50, 30, 20))
        ],
        "excluded_aspects": [],
    }
    rubrics = {
        "rubric_set_id": "syn_tri_rubrics",
        "version": "0.1.0",
        "scorecard_id": "syn_tri_scorecard",
        "scorecard_version": "0.1",
        "rubrics": [
            {
                "expectation_key": key,
                "criterion_id": cid,
                "expectation_text": text,
                "rubric": "Integrity-framed: addressed AND grounded.",
                "evaluation_steps": ["Check the spans.", "Check the claims."],
                "pass_threshold": 0.7,
                "selection_terms": terms,
                "anchor_sub_section_ids": anchors_of[cid],
            }
            for cid, _rid, key, text, _s, _a, terms in CRITERIA
        ],
    }
    profile = {
        "profile_id": "syn_tri",
        "label": "Synthetic three-criterion profile",
        "instrument": {
            "registry_instrument_type": "SYN-TRI",
            "name": "Synthetic Tri Track",
            "form_name": "Synthetic Tri Assessment Form",
        },
        "option_tag_grammar": {
            "applicable_variant": "Track one",
            "known_variants": ["Track one", "Track two"],
            "variant_prefix": "",
            "all_except_prefix": "all tracks except ",
        },
        "criteria": [
            {"id": cid, "registry_criterion_id": rid, "section_ids": [section_of[cid]]}
            for cid, rid, _k, _t, _s, _a, _terms in CRITERIA
        ],
        "registry_path": "syn/registry.json",
        "scorecard": {"path": "syn/scorecard.json", "scorecard_id": "syn_tri_scorecard", "version": "0.1"},
        "rubric_set": {"path": "syn/rubrics.json", "rubric_set_id": "syn_tri_rubrics", "version": "0.1.0"},
    }
    _write_json(root / "syn/registry.json", registry)
    _write_json(root / "syn/scorecard.json", scorecard)
    _write_json(root / "syn/rubrics.json", rubrics)
    return _write_json(root / "syn/profile.json", profile)


def _section(sub_sections: list[tuple[str, str]], *, claims=True) -> dict:
    return {
        "sub_sections": [
            {"sub_section_id": sid, "title": f"Part {sid}", "content": content}
            for sid, content in sub_sections
        ],
        "validation_status": {
            "claim_statuses": (
                [
                    {
                        "claim_id": "C01",
                        "claim_summary": "The objectives are original.",
                        "status": "confirmed",
                        "source_ref": "docs/t3/a.json",
                    }
                ]
                if claims
                else []
            )
        },
    }


def _candidate(root: Path, *, drop_anchor: str | None = None, drop_section: str | None = None,
               relevant: str = RELEVANT) -> Path:
    """A candidate whose every section carries one relevant anchor paragraph,
    one irrelevant non-anchor paragraph and, in F.2, three rendered table rows.

    The irrelevant paragraph sits outside the anchor on purpose: inside it the
    anchor bonus keeps every paragraph, so only a non-anchor paragraph can be
    excluded as not_relevant.
    """
    cand = root / "candidate"
    sections = {
        "novelty_section": [("N.1", relevant), ("N.2", IRRELEVANT)],
        "reach_section": [("R.1", "The uptake reaches every partner."), ("R.2", IRRELEVANT)],
        "feasibility_section": [
            ("F.1", "The plan has two work packages."),
            ("F.2", "\n\n".join(ROWS)),
            ("F.3", IRRELEVANT),
        ],
    }
    for sid, subs in sections.items():
        if sid == drop_section:
            continue
        subs = [s for s in subs if s[0] != drop_anchor]
        _write_json(cand / f"{sid}.json", _section(subs))
    return cand


@pytest.fixture
def world(tmp_path: Path):
    profile = _synthetic_profile(tmp_path)
    bundle = load_profile_bundle(profile, repo_root=tmp_path)
    return tmp_path, bundle


def _params(**over) -> pf.PackParams:
    base = dict(token_budget=3000, span_budget_fraction=0.6, max_token_budget=None,
                include_claims=True, criterion_token_budget=32768)
    base.update(over)
    return pf.PackParams(**base)


def _realise(world, candidate_dir: Path, **over) -> pf.RealisedPackSet:
    _root, bundle = world
    candidate = ba.load_candidate(candidate_dir, bundle.profile)
    return pf.realise_pack_set(bundle, candidate, _params(**over))


# --------------------------------------------------------------------------- #
# 1. The realised pack set and its hash
# --------------------------------------------------------------------------- #


class TestRealisedPackSet:
    def test_the_hash_is_deterministic_over_the_same_inputs(self, world):
        root, _ = world
        a = _realise(world, _candidate(root))
        b = _realise(world, _candidate(root))
        assert a.hash == b.hash
        assert a.hash.startswith("sha256:")
        assert len(a.packs) == 3 and all(p.pack is not None for p in a.packs)

    def test_the_hash_moves_with_a_changed_sentence(self, world):
        root, _ = world
        a = _realise(world, _candidate(root))
        b = _realise(world, _candidate(root / "other", relevant=RELEVANT + " It also reuses tooling."))
        assert a.hash != b.hash
        moved = [p.expectation_key for p, q in zip(a.packs, b.packs) if p.hash != q.hash]
        assert moved == ["nov-obj"]

    @pytest.mark.parametrize(
        "change",
        [dict(token_budget=2000), dict(include_claims=False), dict(criterion_token_budget=4096)],
    )
    def test_the_hash_moves_with_each_selection_parameter(self, world, change):
        root, _ = world
        cand = _candidate(root)
        assert _realise(world, cand).hash != _realise(world, cand, **change).hash

    def test_a_pack_record_carries_no_machine_path(self, world):
        root, _ = world
        realised = _realise(world, _candidate(root))
        for p in realised.packs:
            assert "section_path" not in p.binding_record
            assert p.binding_record["rendered"] == p.pack.render()

    def test_a_missing_anchor_is_reported_not_raised(self, world):
        root, _ = world
        realised = _realise(world, _candidate(root, drop_anchor="F.2"))
        (feas,) = [p for p in realised.packs if p.expectation_key == "feas-plan"]
        assert feas.pack is None
        assert feas.missing_anchors == ("F.2",)
        assert feas.hash.startswith("sha256:")

    def test_a_missing_section_is_reported(self, world):
        root, _ = world
        realised = _realise(world, _candidate(root, drop_section="reach_section"))
        (reach,) = [p for p in realised.packs if p.expectation_key == "reach-uptake"]
        assert reach.pack is None and reach.section_missing

    def test_criterion_inputs_are_realised_alongside_the_packs(self, world):
        root, _ = world
        realised = _realise(world, _candidate(root))
        assert sorted(c.criterion_id for c in realised.criterion_inputs) == [
            "feasibility", "novelty", "reach"
        ]
        assert all(c.complete for c in realised.criterion_inputs)


# --------------------------------------------------------------------------- #
# 2. The seven things, directory route
# --------------------------------------------------------------------------- #


def _preflight(world, candidate_dir: Path, **over) -> pf.PreflightReport:
    root, bundle = world
    return pf.run_preflight(
        bundle, candidate_dir=candidate_dir, params=_params(**over), repo_root=root,
        clock=lambda: FROZEN,
    )


class TestTheSevenThings:
    def test_anchors_present_against_the_rubrics_the_profile_declares(self, world):
        root, _ = world
        data = _preflight(world, _candidate(root)).to_dict()
        anchors = data["anchors"]
        assert anchors["declared_rubrics"] == 3
        assert anchors["rubrics_with_every_anchor_present"] == 3
        assert anchors["missing"] == []
        by_key = {r["expectation_key"]: r for r in anchors["rubrics"]}
        assert by_key["feas-plan"]["anchors"] == ["F.1", "F.2"]
        assert by_key["feas-plan"]["present"] == ["F.1", "F.2"]

    def test_a_missing_anchor_is_named_and_flagged(self, world):
        root, _ = world
        report = _preflight(world, _candidate(root, drop_anchor="F.2"))
        data = report.to_dict()
        assert data["anchors"]["missing"] == [
            {"expectation_key": "feas-plan", "section_id": "feasibility_section", "anchors": ["F.2"]}
        ]
        assert any("anchor" in f for f in report.flags)

    def test_not_relevant_exclusions_per_expectation_with_their_token_cost(self, world):
        root, _ = world
        data = _preflight(world, _candidate(root)).to_dict()
        per_pack = {p["expectation_key"]: p for p in data["packs"]}
        nov = per_pack["nov-obj"]
        # One irrelevant paragraph and no irrelevant claim: the cost is that paragraph's.
        assert nov["not_relevant"]["spans"] == 1
        # The cost is the rendered span (key line + text), so at least the text itself.
        assert nov["not_relevant"]["tokens"] >= pf.estimate_tokens(IRRELEVANT)
        assert nov["status"] == PACK_COMPLETE  # not_relevant never flips the status
        totals = data["exclusions"]
        assert totals[EXCLUDED_NOT_RELEVANT]["items"] == sum(
            p["not_relevant"]["spans"] + p["not_relevant"]["claims"] for p in data["packs"]
        )
        assert totals[EXCLUDED_NOT_RELEVANT]["tokens"] > 0

    def test_over_budget_exclusions_are_visible_and_flagged(self, world):
        root, _ = world
        # 110 tokens carries the frame and one short paragraph, not two.
        report = _preflight(world, _candidate(root), token_budget=110)
        data = report.to_dict()
        over = [p for p in data["packs"] if p["status"] == PACK_INSUFFICIENT_CONTEXT]
        assert over, data["packs"]
        assert data["exclusions"][EXCLUDED_OVER_BUDGET]["items"] >= 1
        assert any(PACK_INSUFFICIENT_CONTEXT in f for f in report.flags)

    def test_table_rendering_and_row_parse_counts(self, world):
        root, _ = world
        data = _preflight(world, _candidate(root)).to_dict()
        tables = data["tables"]
        assert tables["rows_rendered"] == 3
        assert tables["rows_parsed"] == 3
        assert tables["cells"] == 12
        assert tables["per_section"]["feasibility_section"]["rows_rendered"] == 3
        assert tables["manifest"] is None

    def test_package_and_leakage_are_not_applicable_without_a_package(self, world):
        root, _ = world
        data = _preflight(world, _candidate(root)).to_dict()
        assert data["package"] == pf.NOT_APPLICABLE
        assert data["leakage"] == pf.NOT_APPLICABLE
        assert data["evidence_source"] == ba.EVIDENCE_SOURCE_DIRECTORY

    def test_the_pins_cover_the_candidate_the_profile_and_every_selection_input(self, world):
        root, bundle = world
        cand = _candidate(root)
        data = _preflight(world, cand, include_claims=False).to_dict()
        candidate = ba.load_candidate(cand, bundle.profile)
        assert data["candidate_hash"] == ba.candidate_hash(candidate)
        assert data["profile_version"] == bundle.version
        assert data["rubric_set_fingerprint"] == bundle.rubric_set.fingerprint
        assert data["scorecard_hash"] == bundle.scorecard_hash
        assert data["params"] == {
            "token_budget": 3000,
            "span_budget_fraction": 0.6,
            "max_token_budget": None,
            "include_claims": False,
            "criterion_token_budget": 32768,
        }
        realised = pf.realise_pack_set(bundle, candidate, _params(include_claims=False))
        assert data["pack_set_hash"] == realised.hash
        assert data["advisory"] is True and data["blocking"] is False

    def test_with_claims_withheld_no_claim_is_charged(self, world):
        root, _ = world
        data = _preflight(world, _candidate(root), include_claims=False).to_dict()
        for p in data["packs"]:
            assert p["included"]["claims"] == 0
            assert p["not_relevant"]["claims"] == 0
            assert p["include_claims"] is False

    def test_render_names_every_flag_and_the_hash(self, world):
        root, _ = world
        report = _preflight(world, _candidate(root, drop_anchor="F.2"))
        text = pf.render_preflight(report.to_dict())
        assert "EVIDENCE PREFLIGHT" in text
        assert report.pack_set_hash[:19] in text
        for flag in report.flags:
            assert flag in text


# --------------------------------------------------------------------------- #
# 3. The document route: package, leakage, the esr directory, the manifest
# --------------------------------------------------------------------------- #

CANDIDATE_REL = Path("docs/tier5_deliverables/candidates/synthetic_candidate.json")


@pytest.fixture
def graph_world(tmp_path: Path):
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    import_document(root, CANDIDATE_REL)
    profile = _synthetic_profile(
        root, sections={"novelty": "S1", "reach": "S2", "feasibility": "S3"}
    )
    bundle = load_profile_bundle(profile, repo_root=root)
    return root, bundle


def _evidence(root: Path, bundle, out: Path):
    return ba.build_blind_evidence(root, "CAND-1", profile_version=bundle.version, out_dir=out)


class TestDocumentRoute:
    def test_package_completeness_under_the_package_budget(self, graph_world, tmp_path):
        root, bundle = graph_world
        evidence = _evidence(root, bundle, tmp_path / "out")
        report = pf.run_preflight(
            bundle, evidence=evidence, params=_params(), graph_root=root, repo_root=root,
            clock=lambda: FROZEN,
        )
        data = report.to_dict()
        assert data["evidence_source"] == ba.EVIDENCE_SOURCE_DEV_GRAPH
        assert data["package"]["completeness"] == "complete"
        assert data["package"]["budget"] == ba.DEFAULT_PACKAGE_BUDGET
        assert data["package"]["included"] == len(evidence.package.items)
        assert data["package_id"] == evidence.package.package_id
        assert data["snapshot_id"] == evidence.snapshot_id

    def test_the_leakage_section_says_esr_is_never_snapshotted(self, graph_world, tmp_path):
        root, bundle = graph_world
        # An ESR record planted where the spec keeps it: under Tier 4, outside the dev-graph.
        esr = root / "docs/tier4_orchestration_state/some_project/esr/historical-esr.json"
        _write_json(esr, {"record_type": "esr", "score": 85.8})
        evidence = _evidence(root, bundle, tmp_path / "out")
        data = pf.run_preflight(
            bundle, evidence=evidence, params=_params(), graph_root=root, repo_root=root,
            clock=lambda: FROZEN,
        ).to_dict()
        leakage = data["leakage"]
        assert leakage["guard"]["passed"] is True
        assert leakage["guard"]["items_checked"] == len(evidence.package.items)
        esr_section = leakage["esr"]
        assert esr_section["snapshot_inputs"] == len(build_snapshot(root).inputs)
        assert esr_section["inputs_under_esr"] == []
        assert esr_section["esr_directories"] == [
            {
                "path": "docs/tier4_orchestration_state/some_project/esr",
                "under_graph_root": True,
                "read_by_snapshot": False,
            }
        ]
        assert esr_section["never_snapshotted"] is True

    def test_the_word_scan_runs_over_the_graph_root(self, graph_world, tmp_path):
        root, bundle = graph_world
        evidence = _evidence(root, bundle, tmp_path / "out")
        data = pf.run_preflight(
            bundle, evidence=evidence, params=_params(), graph_root=root, repo_root=root,
            clock=lambda: FROZEN,
        ).to_dict()
        scan = data["leakage"]["word_scan"]
        assert scan["files_scanned"] > 0
        assert scan["ok"] is True
        assert scan["new_violations"] == 0

    def test_an_import_manifest_is_pinned_by_hash_and_versions(self, graph_world, tmp_path):
        root, bundle = graph_world
        manifest = _write_json(
            root / "docs/tier4_orchestration_state/dev_graph/imports/CAND-1.json",
            {
                "record_type": "external_proposal_import_manifest",
                "versions": {"extractor": "1.0.0", "normalisation": "1.0.0", "table_rendering": "1.0.0"},
                "tables": {"count": 0, "rows_rendered": 0, "rows_parsed": 0},
            },
        )
        evidence = _evidence(root, bundle, tmp_path / "out")
        data = pf.run_preflight(
            bundle, evidence=evidence, params=_params(), graph_root=root, repo_root=root,
            clock=lambda: FROZEN,
        ).to_dict()
        pin = data["import_manifest"]
        assert pin["path"] == "docs/tier4_orchestration_state/dev_graph/imports/CAND-1.json"
        assert pin["sha256"] == pf.file_sha256(manifest)
        assert pin["versions"]["extractor"] == "1.0.0"
        assert data["tables"]["manifest"] == {"count": 0, "rows_rendered": 0, "rows_parsed": 0}
        assert data["tables"]["agrees_with_manifest"] is True


# --------------------------------------------------------------------------- #
# 4. The command: preflight writes, assess requires and re-binds
# --------------------------------------------------------------------------- #


class DualBackend:
    def __init__(self):
        self.calls = 0

    def __call__(self, messages):
        self.calls += 1
        system = "\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "system")
        if "CRITERION UNDER ASSESSMENT" in system:
            return {"content": CRITERION_JSON}
        return {"content": PASS_JSON}


def _judge(tmp_path: Path) -> Judge:
    return Judge(
        JudgeConfig(model="fake-assessor", version="pin-pe05"),
        backend=DualBackend(),
        provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
        clock=lambda: FROZEN,
    )


def _evidence_args(world, candidate: Path, out: Path) -> list[str]:
    root, bundle = world
    return ["--candidate", str(candidate), "--out-dir", str(out),
            "--repo-root", str(root), "--profile", str(bundle.profile.source_path)]


class TestCommand:
    def test_preflight_writes_a_report_and_exits_0_when_nothing_is_flagged(self, world, tmp_path):
        root, _ = world
        out = tmp_path / "reports"
        code = cmd.main(["preflight", *_evidence_args(world, _candidate(root), out)], clock=lambda: FROZEN)
        assert code == 0
        (path,) = list(out.iterdir())
        assert path.name.startswith("preflight_")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["record_type"] == pf.PREFLIGHT_RECORD_TYPE
        assert data["flags"] == []

    def test_preflight_exits_1_when_something_is_flagged_and_still_writes(self, world, tmp_path):
        root, _ = world
        out = tmp_path / "reports"
        code = cmd.main(
            ["preflight", *_evidence_args(world, _candidate(root, drop_anchor="F.2"), out)],
            clock=lambda: FROZEN,
        )
        assert code == 1
        (path,) = list(out.iterdir())
        assert json.loads(path.read_text(encoding="utf-8"))["flags"]

    def test_preflight_never_overwrites(self, world, tmp_path):
        root, _ = world
        out = tmp_path / "reports"
        args = _evidence_args(world, _candidate(root), out)
        assert cmd.main(["preflight", *args], clock=lambda: FROZEN) == 0
        assert cmd.main(["preflight", *args], clock=lambda: FROZEN) == 0
        names = sorted(p.name for p in out.iterdir())
        assert len(names) == 2 and names[0] != names[1]

    def test_assess_requires_a_preflight(self, world, tmp_path):
        root, _ = world
        with pytest.raises(SystemExit) as exc:
            cmd.main(["assess", *_evidence_args(world, _candidate(root), tmp_path / "r")],
                     judge=_judge(tmp_path), clock=lambda: FROZEN)
        assert exc.value.code == 2

    def test_assess_re_binds_the_preflight_hash_onto_the_report(self, world, tmp_path):
        root, _ = world
        out = tmp_path / "reports"
        cand = _candidate(root)
        args = _evidence_args(world, cand, out)
        assert cmd.main(["preflight", *args], clock=lambda: FROZEN) == 0
        (preflight_path,) = list(out.iterdir())
        code = cmd.main(["assess", *args, "--preflight", str(preflight_path)],
                        judge=_judge(tmp_path), clock=lambda: FROZEN)
        assert code == 0
        (report_path,) = [p for p in out.iterdir() if p.name.startswith("blind_")]
        report = json.loads(report_path.read_text(encoding="utf-8"))
        preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        assert report["preflight_pack_set_hash"] == preflight["pack_set_hash"]
        assert report["preflight_report"] == preflight_path.as_posix()
        # verify re-binds and shows the hash
        assert cmd.main(["verify", "--report", str(report_path), "--candidate", str(cand),
                         "--repo-root", str(root), "--profile", str(world[1].profile.source_path)]) == 0

    def test_a_changed_candidate_invalidates_the_preflight(self, world, tmp_path, capsys):
        root, _ = world
        out = tmp_path / "reports"
        cand = _candidate(root)
        args = _evidence_args(world, cand, out)
        assert cmd.main(["preflight", *args], clock=lambda: FROZEN) == 0
        (preflight_path,) = list(out.iterdir())
        section = cand / "novelty_section.json"
        data = json.loads(section.read_text(encoding="utf-8"))
        data["sub_sections"][0]["content"] += "\n\nA new objective was added after the preflight."
        section.write_text(json.dumps(data), encoding="utf-8")
        code = cmd.main(["assess", *args, "--preflight", str(preflight_path)],
                        judge=_judge(tmp_path), clock=lambda: FROZEN)
        assert code == 2
        err = capsys.readouterr().err
        assert "candidate_hash" in err and "nov-obj" in err
        assert not [p for p in out.iterdir() if p.name.startswith("blind_")]

    def test_a_changed_budget_invalidates_the_preflight_and_is_named(self, world, tmp_path, capsys):
        root, _ = world
        out = tmp_path / "reports"
        args = _evidence_args(world, _candidate(root), out)
        assert cmd.main(["preflight", *args], clock=lambda: FROZEN) == 0
        (preflight_path,) = list(out.iterdir())
        code = cmd.main(["assess", *args, "--preflight", str(preflight_path), "--budget", "2000"],
                        judge=_judge(tmp_path), clock=lambda: FROZEN)
        assert code == 2
        err = capsys.readouterr().err
        assert "token_budget" in err and "3000" in err and "2000" in err

    def test_a_preflight_over_another_profile_is_refused(self, world, tmp_path, capsys):
        root, bundle = world
        out = tmp_path / "reports"
        args = _evidence_args(world, _candidate(root), out)
        assert cmd.main(["preflight", *args], clock=lambda: FROZEN) == 0
        (preflight_path,) = list(out.iterdir())
        data = json.loads(preflight_path.read_text(encoding="utf-8"))
        data["profile_version"] = "sha256:" + "0" * 64
        tampered = _write_json(tmp_path / "tampered.json", data)
        code = cmd.main(["assess", *args, "--preflight", str(tampered)],
                        judge=_judge(tmp_path), clock=lambda: FROZEN)
        assert code == 2
        assert "profile_version" in capsys.readouterr().err

    def test_the_library_default_still_takes_no_preflight(self, world, tmp_path):
        root, bundle = world
        report = ba.assess_candidate(_judge(tmp_path), bundle, _candidate(root), clock=lambda: FROZEN)
        assert report.preflight_pack_set_hash == ""
        assert report.to_dict()["preflight_pack_set_hash"] == ""


# --------------------------------------------------------------------------- #
# 5. The shipped candidate, re-derived offline
# --------------------------------------------------------------------------- #

WORKSPACE = REPO / "workspaces" / "msca_dn"
DN_PROFILE = REPO / "harness" / "profiles" / "msca_dn_2026_default.json"
DN_DOCUMENT = "MSCA-DN-2025_sanitised_part_b"


@pytest.mark.skipif(not WORKSPACE.is_dir(), reason="the DN workspace is not on this branch")
class TestShippedCandidate:
    @pytest.fixture(scope="class")
    def preflight(self, tmp_path_factory):
        bundle = load_profile_bundle(DN_PROFILE, repo_root=REPO)
        out = tmp_path_factory.mktemp("dn")
        evidence = ba.build_blind_evidence(WORKSPACE, DN_DOCUMENT, profile_version=bundle.version, out_dir=out)
        # The blind lane's own parameters: the subscription transport has no
        # ceiling and the imported ledger is withheld (spec decisions 6 and 10).
        params = pf.PackParams(
            token_budget=32768, span_budget_fraction=0.6, max_token_budget=None,
            include_claims=False, criterion_token_budget=32768,
        )
        report = pf.run_preflight(
            bundle, evidence=evidence, params=params, graph_root=WORKSPACE, repo_root=REPO,
            clock=lambda: FROZEN,
        )
        return bundle, evidence, report.to_dict()

    def test_the_ten_anchors_are_present(self, preflight):
        _b, _e, data = preflight
        assert data["anchors"]["declared_rubrics"] == 10
        assert data["anchors"]["rubrics_with_every_anchor_present"] == 10
        assert data["anchors"]["missing"] == []

    def test_every_pack_and_criterion_input_is_complete_under_the_blind_lane_budgets(self, preflight):
        _b, _e, data = preflight
        assert [p["status"] for p in data["packs"]] == [PACK_COMPLETE] * 10
        assert all(c["complete"] for c in data["criterion_inputs"])
        assert data["exclusions"][EXCLUDED_OVER_BUDGET]["items"] == 0

    def test_not_relevant_volume_is_visible(self, preflight):
        _b, _e, data = preflight
        assert data["exclusions"][EXCLUDED_NOT_RELEVANT]["items"] > 0
        assert data["exclusions"][EXCLUDED_NOT_RELEVANT]["tokens"] > 0

    def test_the_tables_agree_with_the_import_manifest(self, preflight):
        _b, _e, data = preflight
        assert data["tables"]["rows_rendered"] == 88
        assert data["tables"]["rows_parsed"] == 88
        assert data["tables"]["agrees_with_manifest"] is True
        assert data["import_manifest"]["versions"]["extractor"] == "1.0.0"

    def test_package_complete_and_nothing_leaks(self, preflight):
        _b, _e, data = preflight
        assert data["package"]["completeness"] == "complete"
        assert data["leakage"]["guard"]["passed"] is True
        assert data["leakage"]["esr"]["never_snapshotted"] is True
        assert data["leakage"]["word_scan"]["ok"] is True

    def test_the_preflight_carries_no_flag(self, preflight):
        _b, _e, data = preflight
        assert data["flags"] == []
