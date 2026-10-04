"""PE-01 — Workspace, intake and provenance freeze.

Acceptance, from ``plans/msca_dn_pre_evaluation_spec.md`` §7 PE-01:

* Every input has a declared version and role, and the declaration is
  re-derived here from the stored files (hash, page count, version marker).
* No demo record is reachable from the real graph root.
* The sanitised candidate is nowhere described as the submitted version.
* The intake's ``call_id`` is the historical call and differs from the
  baseline's target call, because no engine path checks it.

Plus the repository's own rule for authored artifacts: the authoring tool
replays byte-equal (``--check`` exits 0 on the committed tree).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from runner.dev_graph import DevGraphError, build_snapshot, read_esr_intake
from runner.dev_graph.builder import SOURCES_REL
from runner.dev_graph.intake import INTAKE_REL
from runner.paths import find_repo_root
from runner.source_index import read_page_text
from tools import author_msca_dn_workspace as ws

REPO = find_repo_root()
WORKSPACE = REPO / ws.WORKSPACE_REL
REGISTER = REPO / ws.REGISTER_REL
SOURCE_DIR = REPO / ws.SOURCE_DIR_REL
#: The baseline target call's owner (spec PE-01, built at PE-02).
DN_PROFILE = REPO / "harness/profiles/msca_dn_2026_default.json"

#: The spec's §1 table, first 16 hex of each sha256. Typed from the spec on
#: purpose: the test must catch a swapped or re-saved file, so it cannot read
#: the expected value from the artifact under test.
SPEC_HASH_PREFIXES = {
    "candidate": "5474569f33d20174",
    "esr": "40a885e8aa593367",
    "evaluation_form": "f7478ef7f1eac4c3",
    "application_form_submission": "b77f148e8875359a",
    "application_form_baseline": "f19042696e492ce4",
    "application_form_baseline_rtf": "00a48b993fe013ac",
}

FORBIDDEN_PHRASES = re.compile(
    r"(?i)\b(the submitted version|as submitted|submitted document|submitted proposal|"
    r"submitted text|the original submission text)\b"
)
#: A negated mention ("not the submitted text") is the statement the ticket
#: wants, so it is removed before the positive-mention check runs.
NEGATED_MENTION = re.compile(r"(?i)\bnot the submitted \w+")


def _register() -> dict:
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def _authored_texts() -> dict[Path, str]:
    paths = [
        REGISTER,
        WORKSPACE / "README.md",
        WORKSPACE / SOURCES_REL,
        WORKSPACE / INTAKE_REL / f"{ws.INTAKE_ID}.json",
    ]
    return {p: p.read_text(encoding="utf-8") for p in paths}


# --------------------------------------------------------------------------- #
# The originals moved, untouched
# --------------------------------------------------------------------------- #


class TestOriginals:
    def test_both_pdfs_live_beside_the_register_and_nowhere_else_in_tier_3(self) -> None:
        tier3_sources = REPO / "docs/tier3_project_instantiation/source_materials"
        for name in ("sanitized_proposal_final.pdf", "MSCA DN ESR.pdf"):
            hits = sorted(p.relative_to(REPO).as_posix() for p in tier3_sources.rglob(name))
            assert hits == [(ws.SOURCE_DIR_REL / name).as_posix()], hits

    def test_the_moved_files_carry_the_spec_hashes(self) -> None:
        for name, key in (("sanitized_proposal_final.pdf", "candidate"), ("MSCA DN ESR.pdf", "esr")):
            digest = hashlib.sha256((SOURCE_DIR / name).read_bytes()).hexdigest()
            assert digest.startswith(SPEC_HASH_PREFIXES[key]), (name, digest)


# --------------------------------------------------------------------------- #
# The fidelity register's provenance header
# --------------------------------------------------------------------------- #


class TestRegisterProvenance:
    def test_record_shape(self) -> None:
        reg = _register()
        assert reg["record_type"] == ws.REGISTER_RECORD_TYPE
        assert "schema_ref" in reg and "§16.3" in reg["schema_ref"]
        prov = reg["provenance"]
        assert prov["kind"] == "declared"
        for key in (
            "historical_submission",
            "current_assessment_artifact",
            "transformation",
            "relationship_to_esr",
            "authoritative_original",
        ):
            assert key in prov, key

    def test_every_input_has_a_role_a_version_and_a_hash_that_rederives(self) -> None:
        inputs = _register()["provenance"]["inputs"]
        assert {i["role_key"] for i in inputs} == set(SPEC_HASH_PREFIXES)
        for item in inputs:
            path = REPO / item["path"]
            assert path.is_file(), item["path"]
            assert item["role"].strip() and item["version"].strip(), item
            assert item["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest(), item["path"]
            assert item["sha256"].startswith(SPEC_HASH_PREFIXES[item["role_key"]]), item["path"]

    def test_page_counts_and_version_markers_rederive_from_the_pdfs(self) -> None:
        for item in _register()["provenance"]["inputs"]:
            path = REPO / item["path"]
            if path.suffix.lower() != ".pdf":
                assert "pages" not in item
                continue
            assert item["pages"] == ws.pdf_page_count(path), item["path"]
            text = ws.pdf_text(path)
            for marker in item["version_markers"]:
                assert marker in text, (item["path"], marker)

    def test_the_candidate_is_declared_a_derivative_not_the_submitted_document(self) -> None:
        prov = _register()["provenance"]
        current = prov["current_assessment_artifact"]
        assert current["is_submitted_document"] is False
        assert current["pages"] == 84
        assert prov["transformation"]["reflow"]["original_pages"] == 34

    def test_the_dn_type_phrase_is_on_the_declared_page(self) -> None:
        candidate = REPO / ws.CANDIDATE_PDF_REL
        assert ws.DN_TYPE_MARKER in read_page_text(candidate, ws.DN_TYPE_PAGE)

    def test_the_register_carries_no_esr_content(self) -> None:
        # Decision 12: ESR content lives only in the Tier 4 record of PE-08.
        text = REGISTER.read_text(encoding="utf-8")
        for token in (r"\b85\.80\b", r"\b4\.20\b", r"\b4\.50\b", "esr_scores", "baseline_target"):
            assert re.search(token, text) is None, token

    def test_the_two_halves_are_marked_and_the_derived_half_is_pending(self) -> None:
        reg = _register()
        assert reg["derived"]["kind"] == "derived"
        assert reg["derived"]["status"] == "pending"
        assert reg["declared"]["kind"] == "declared"
        assert reg["declared"]["sub_sections"] == []

    def test_no_authored_text_calls_the_candidate_the_submitted_version(self) -> None:
        for path, text in _authored_texts().items():
            hit = FORBIDDEN_PHRASES.search(NEGATED_MENTION.sub("", text))
            assert hit is None, (path.relative_to(REPO).as_posix(), hit.group(0) if hit else None)


# --------------------------------------------------------------------------- #
# The intake record under the real graph root
# --------------------------------------------------------------------------- #


class TestIntake:
    def test_the_intake_reads_back_through_the_engine(self) -> None:
        intake = read_esr_intake(WORKSPACE, ws.INTAKE_ID)
        assert intake.document_id == ws.DOCUMENT_ID
        assert intake.prior_submission is True
        assert intake.esr_availability == "available"
        assert intake.permitted_purpose == "blind_pre_evaluation"
        assert intake.esr_reference

    def test_call_id_is_the_historical_call_and_not_the_baseline_target(self) -> None:
        # No engine path reads call_id (spec PE-01), so this is the only check.
        # The target call is read from its owner, the PE-02 profile; the
        # workspace tool carries no copy of it.
        intake = read_esr_intake(WORKSPACE, ws.INTAKE_ID)
        profile = json.loads(DN_PROFILE.read_text(encoding="utf-8"))
        target = profile["target_call"]["call_id"]
        assert intake.call_id == ws.HISTORICAL_CALL_ID
        assert intake.call_id != target
        assert "2025" in intake.call_id and "2026" in target
        assert not hasattr(ws, "BASELINE_TARGET_CALL_ID"), "the profile owns the target call"

    def test_the_profile_is_the_only_dn_profile_and_names_the_target_call(self) -> None:
        profiles = sorted((REPO / "harness/profiles").glob("msca_dn*.json"))
        assert profiles == [DN_PROFILE]
        profile = json.loads(DN_PROFILE.read_text(encoding="utf-8"))
        assert profile["target_call"]["call_id"] == "HORIZON-MSCA-2026-DN-01"

    def test_the_esr_reference_names_the_esr_by_hash_and_the_register(self) -> None:
        intake = read_esr_intake(WORKSPACE, ws.INTAKE_ID)
        esr = SOURCE_DIR / "MSCA DN ESR.pdf"
        assert intake.esr_reference is not None
        assert hashlib.sha256(esr.read_bytes()).hexdigest() in intake.esr_reference
        assert ws.REGISTER_REL.as_posix() in intake.esr_reference
        assert esr.relative_to(REPO).as_posix() in intake.esr_reference


# --------------------------------------------------------------------------- #
# Isolation: the real graph root reaches no demo record
# --------------------------------------------------------------------------- #


class TestIsolation:
    def test_workspace_is_a_graph_root_with_nothing_in_it_yet(self) -> None:
        snap = build_snapshot(WORKSPACE)
        assert all(not Path(p).is_absolute() for p in snap.inputs)
        assert tuple(snap.inputs) == (SOURCES_REL.as_posix(),)
        assert len(snap.nodes) == 0

    def test_no_demo_node_or_input_is_reachable_from_the_workspace(self) -> None:
        demo = build_snapshot(REPO)
        real = build_snapshot(WORKSPACE)
        assert len(demo.nodes) > 0
        assert {n["id"] for n in real.nodes}.isdisjoint({n["id"] for n in demo.nodes})
        for rel in real.inputs:
            assert (WORKSPACE / rel).is_file()

    def test_the_demo_intake_is_not_readable_from_the_workspace(self) -> None:
        with pytest.raises(DevGraphError):
            read_esr_intake(WORKSPACE, "demo-biodiv-2027-part-b-v1")

    def test_no_symlink_or_reference_out_of_the_workspace(self) -> None:
        for path in WORKSPACE.rglob("*"):
            assert not path.is_symlink(), path
        demo_sources = REPO / SOURCES_REL
        assert json.loads(demo_sources.read_text(encoding="utf-8-sig"))["sources"]
        assert json.loads((WORKSPACE / SOURCES_REL).read_text(encoding="utf-8"))["sources"] == []


# --------------------------------------------------------------------------- #
# Byte-equal replay
# --------------------------------------------------------------------------- #


class TestReplay:
    def test_check_mode_passes_on_the_committed_tree(self) -> None:
        assert ws.main(["--check"]) == 0

    def test_rendering_is_deterministic(self) -> None:
        assert ws.render_all(REPO) == ws.render_all(REPO)

    def test_rendered_bytes_match_the_committed_files(self) -> None:
        for rel, data in ws.render_all(REPO).items():
            assert (REPO / rel).read_bytes() == data, rel
