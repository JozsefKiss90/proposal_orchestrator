"""
Candidate provenance (ticket V05): the audit's wording derived from the records
one candidate's import wrote, never from a constant applied to every document.

Four groups:

* :func:`declared_word` — the narrow rule that reads one declared value, and
  the values it refuses to read.
* The derivation over a synthetic manifest and register: the sanitised case,
  the referenced case, and every contradiction or gap between the operator's
  declaration and the importer's measurement.
* Finding the manifest: by node id, by document id, and the ambiguity it
  refuses to guess through.
* The real committed records: both revisions derive the wording the committed
  audits carry, with no flag.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import harness.candidate_provenance as cp
from runner.paths import find_repo_root

REPO = find_repo_root()
DN_WORKSPACE = REPO / "workspaces" / "msca_dn"
DN_DOCUMENT = "MSCA-DN-2025_sanitised_part_b"


# --------------------------------------------------------------------------- #
# A synthetic manifest and register
# --------------------------------------------------------------------------- #


def _write(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return path


#: The measured half of a sanitised candidate: the importer found no marker.
NO_MARKERS = {"bracketed_numbers": 0, "doi": 0, "url": 0, "author_year": 0}


def _world(
    root: Path,
    *,
    citations: object = "all removed; no bracketed numbers, DOIs, URLs or reference list",
    identifiers: object = "generalised (project acronym, partner names, people, places)",
    is_submitted: object = False,
    marker_counts: object = NO_MARKERS,
    declared_status: object = "Unresolved",
    register_rel: object = "src/register.json",
    node_id: str = "DOC-1@aaaa",
    document_id: str = "DOC-1",
    manifest_name: str = "DOC-1.json",
) -> Path:
    """One manifest and the register it names, under *root* as the repo root."""
    register: dict = {
        "record_type": "fidelity_register",
        "provenance": {
            "current_assessment_artifact": {},
            "transformation": {},
        },
        "derived": {},
    }
    if is_submitted is not None:
        register["provenance"]["current_assessment_artifact"]["is_submitted_document"] = is_submitted
    if citations is not None:
        register["provenance"]["transformation"]["citations"] = citations
    if identifiers is not None:
        register["provenance"]["transformation"]["identifiers"] = identifiers
    if marker_counts is not None:
        register["derived"]["citation_marker_counts"] = marker_counts
    if isinstance(register_rel, str):
        _write(root / register_rel, register)
    manifest: dict = {
        "record_type": "external_proposal_import_manifest",
        "candidate": {},
        "claims": {},
        "document": {"node_id": node_id, "document_id": document_id},
    }
    if register_rel is not None:
        manifest["candidate"]["fidelity_register"] = register_rel
    if declared_status is not None:
        manifest["claims"]["declared_status"] = declared_status
    return _write(root / cp.IMPORT_MANIFESTS_REL / manifest_name, manifest)


#: A candidate that still cites its sources and names its real participants.
_REFERENCED = {
    "citations": "retained; the submitted reference list is intact",
    "identifiers": "unchanged",
    "is_submitted": True,
    "marker_counts": {"bracketed_numbers": 61, "doi": 4, "url": 2, "author_year": 0},
}


# --------------------------------------------------------------------------- #
# declared_word
# --------------------------------------------------------------------------- #


class TestDeclaredWord:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("all removed; no bracketed numbers, DOIs, URLs or reference list", "removed"),
            ("generalised (project acronym, partner names, people, places)", "generalised"),
            ("Removed.", "removed"),
            ("  all   stripped ", "stripped"),
            ("unchanged", "unchanged"),
            ("", ""),
            ("all", ""),
            (None, ""),
            (42, ""),
            (["removed"], ""),
        ],
    )
    def test_only_the_leading_word_is_read(self, value, expected):
        assert cp.declared_word(value) == expected

    def test_a_value_in_no_vocabulary_matches_neither_side(self):
        word = cp.declared_word("partially obscured in places")
        assert word not in cp.CITATIONS_REMOVED_WORDS
        assert word not in cp.CITATIONS_PRESENT_WORDS


# --------------------------------------------------------------------------- #
# The derivation
# --------------------------------------------------------------------------- #


class TestSanitisedCandidate:
    def test_three_statements_agreeing_name_sanitisation(self, tmp_path):
        manifest = _world(tmp_path)
        p = cp.provenance_from_manifest(manifest, repo_root=tmp_path)
        assert p.grounding_cause == cp.CAUSE_SANITISATION
        assert p.grounding_reason == "supporting sources removed by sanitisation"
        assert p.identity_scope == cp.IDENTITY_GENERALISED
        assert p.identities_are_comparable is False
        assert p.identity_statement == cp.STATEMENT_GENERALISED
        assert p.expected_ledger_status == "unresolved"
        assert p.is_submitted_document is False
        assert p.flags == ()

    def test_the_basis_names_the_declaration_and_the_measurement(self, tmp_path):
        p = cp.provenance_from_manifest(_world(tmp_path), repo_root=tmp_path)
        assert any("citation_marker_counts measures 0 marker(s)" in b for b in p.basis)
        assert any("read as removed" in b for b in p.basis)
        assert any("read as generalised" in b for b in p.basis)
        assert any("claim ledger carries status 'unresolved'" in b for b in p.basis)
        assert [s.split("/")[-1] for s in p.sources] == ["DOC-1.json", "register.json"]


class TestReferencedCandidate:
    """Criterion 3: an anonymised-host assumption is never an original's rule."""

    def test_measured_markers_make_the_sources_present_and_unresolved(self, tmp_path):
        p = cp.provenance_from_manifest(_world(tmp_path, **_REFERENCED), repo_root=tmp_path)
        assert p.grounding_cause == cp.CAUSE_SOURCES_PRESENT
        assert p.grounding_reason == cp.REASON_SOURCES_PRESENT
        assert p.flags == ()

    def test_identifiers_as_submitted_make_the_identities_comparable(self, tmp_path):
        p = cp.provenance_from_manifest(_world(tmp_path, **_REFERENCED), repo_root=tmp_path)
        assert p.identity_scope == cp.IDENTITY_AS_SUBMITTED
        assert p.identities_are_comparable is True
        assert p.identity_statement == ""

    def test_no_sanitisation_wording_reaches_a_referenced_candidate(self, tmp_path):
        p = cp.provenance_from_manifest(_world(tmp_path, **_REFERENCED), repo_root=tmp_path)
        wording = " ".join(
            [p.grounding_cause, p.grounding_reason, p.identity_scope, p.identity_statement,
             *p.basis, *p.flags]
        )
        assert "sanitis" not in wording and "sanitiz" not in wording


class TestContradictionsAndGaps:
    def test_declared_removed_but_markers_measured_the_measurement_governs(self, tmp_path):
        manifest = _world(tmp_path, marker_counts={"doi": 3})
        p = cp.provenance_from_manifest(manifest, repo_root=tmp_path)
        assert p.grounding_cause == cp.CAUSE_SOURCES_PRESENT
        assert any("the measurement governs" in f for f in p.flags)

    def test_declared_present_and_none_measured_is_unresolved(self, tmp_path):
        manifest = _world(tmp_path, citations="retained")
        p = cp.provenance_from_manifest(manifest, repo_root=tmp_path)
        assert p.grounding_cause == cp.CAUSE_UNSTATED
        assert p.grounding_reason == cp.REASON_UNSTATED
        assert any("declares the citations present and the importer measured none" in f for f in p.flags)

    def test_removal_without_a_derivative_declaration_does_not_name_sanitisation(self, tmp_path):
        manifest = _world(tmp_path, is_submitted=True)
        p = cp.provenance_from_manifest(manifest, repo_root=tmp_path)
        assert p.grounding_cause == cp.CAUSE_UNSTATED
        assert any("does not" in f and "derivative" in f for f in p.flags)

    def test_an_unmeasured_capability_concludes_nothing(self, tmp_path):
        manifest = _world(tmp_path, marker_counts=None)
        p = cp.provenance_from_manifest(manifest, repo_root=tmp_path)
        assert p.grounding_cause == cp.CAUSE_UNSTATED
        assert any("the markers were not measured" in b for b in p.basis)

    def test_a_non_numeric_count_is_not_a_measurement(self, tmp_path):
        manifest = _world(tmp_path, marker_counts={"doi": "none"})
        p = cp.provenance_from_manifest(manifest, repo_root=tmp_path)
        assert p.grounding_cause == cp.CAUSE_UNSTATED
        assert any("non-numeric count" in b for b in p.basis)

    def test_an_unrecognised_identifier_declaration_borrows_no_statement(self, tmp_path):
        manifest = _world(tmp_path, identifiers="mostly obscured, some left in place")
        p = cp.provenance_from_manifest(manifest, repo_root=tmp_path)
        assert p.identity_scope == cp.IDENTITY_UNSTATED
        assert p.identity_statement == cp.STATEMENT_UNSTATED
        assert "sanitisation" not in p.identity_statement
        assert any("in no recognised vocabulary" in f for f in p.flags)

    def test_a_missing_ledger_declaration_leaves_no_expectation(self, tmp_path):
        manifest = _world(tmp_path, declared_status=None)
        p = cp.provenance_from_manifest(manifest, repo_root=tmp_path)
        assert p.expected_ledger_status is None
        assert any("declares no claims.declared_status" in f for f in p.flags)
        # The grounding cause is independent of the ledger declaration.
        assert p.grounding_cause == cp.CAUSE_SANITISATION

    def test_a_manifest_naming_no_register_states_nothing(self, tmp_path):
        manifest = _world(tmp_path, register_rel=None)
        p = cp.provenance_from_manifest(manifest, repo_root=tmp_path)
        assert p.grounding_cause == cp.CAUSE_UNSTATED
        assert p.identity_scope == cp.IDENTITY_UNSTATED
        assert any("names no candidate.fidelity_register" in f for f in p.flags)

    def test_a_named_register_that_is_absent_is_a_refusal(self, tmp_path):
        manifest = _world(tmp_path, register_rel="src/register.json")
        (tmp_path / "src/register.json").unlink()
        with pytest.raises(cp.CandidateProvenanceError, match="fidelity register not found"):
            cp.provenance_from_manifest(manifest, repo_root=tmp_path)

    def test_a_manifest_that_is_not_json_is_a_refusal(self, tmp_path):
        bad = tmp_path / "m.json"
        bad.write_text("{not json", encoding="utf-8")
        with pytest.raises(cp.CandidateProvenanceError, match="is not valid JSON"):
            cp.provenance_from_manifest(bad, repo_root=tmp_path)


# --------------------------------------------------------------------------- #
# The record's own invariants
# --------------------------------------------------------------------------- #


class TestRecordInvariants:
    def test_every_cause_has_exactly_one_reason(self):
        assert set(cp.GROUNDING_REASONS) == set(cp.GROUNDING_CAUSES)
        assert len(set(cp.GROUNDING_REASONS.values())) == len(cp.GROUNDING_CAUSES)

    def test_every_scope_has_its_own_statement(self):
        assert set(cp.IDENTITY_STATEMENTS) == set(cp.IDENTITY_SCOPES)
        # The comparable scope is the one with nothing to excuse.
        assert cp.IDENTITY_STATEMENTS[cp.IDENTITY_AS_SUBMITTED] == ""
        assert all(
            cp.IDENTITY_STATEMENTS[s] for s in cp.IDENTITY_SCOPES if s != cp.IDENTITY_AS_SUBMITTED
        )

    @pytest.mark.parametrize("cause", cp.GROUNDING_CAUSES)
    def test_the_reason_is_derived_from_the_cause_not_carried_beside_it(self, cause):
        """A record cannot be built with one cause and another's reason: the
        wording is a property of the cause, so there is nothing to disagree."""
        p = cp.CandidateProvenance(grounding_cause=cause, identity_scope=cp.IDENTITY_UNSTATED)
        assert p.grounding_reason == cp.GROUNDING_REASONS[cause]
        with pytest.raises(AttributeError):
            p.grounding_reason = "something else"  # type: ignore[misc]

    @pytest.mark.parametrize("scope", cp.IDENTITY_SCOPES)
    def test_the_statement_is_derived_from_the_scope(self, scope):
        p = cp.CandidateProvenance(grounding_cause=cp.CAUSE_UNSTATED, identity_scope=scope)
        assert p.identity_statement == cp.IDENTITY_STATEMENTS[scope]
        assert bool(p.identity_statement) is not p.identities_are_comparable

    @pytest.mark.parametrize(
        "cause,scope,match",
        [
            ("nonsense", cp.IDENTITY_UNSTATED, "unknown grounding cause"),
            (cp.CAUSE_UNSTATED, "nonsense", "unknown identity scope"),
        ],
    )
    def test_a_value_outside_the_closed_set_is_refused(self, cause, scope, match):
        with pytest.raises(ValueError, match=match):
            cp.CandidateProvenance(grounding_cause=cause, identity_scope=scope)

    def test_the_unstated_default_states_its_own_ignorance(self):
        p = cp.UNSTATED_PROVENANCE
        assert p.grounding_cause == cp.CAUSE_UNSTATED
        assert p.identities_are_comparable is False
        assert p.expected_ledger_status is None
        assert "Unresolved" in p.grounding_reason
        assert "sanitisation" not in p.grounding_reason
        assert "sanitisation" not in p.identity_statement


# --------------------------------------------------------------------------- #
# Finding the manifest
# --------------------------------------------------------------------------- #


class TestFindAndResolve:
    def test_the_node_id_selects_the_revision(self, tmp_path):
        _world(tmp_path, node_id="DOC-1@first", manifest_name="DOC-1.json")
        _world(tmp_path, node_id="DOC-1@second", manifest_name="DOC-1.second.json")
        found = cp.find_import_manifest(tmp_path, node_id="DOC-1@second")
        assert found is not None and found.name == "DOC-1.second.json"

    def test_a_document_id_with_two_revisions_is_not_guessed(self, tmp_path):
        _world(tmp_path, node_id="DOC-1@first", manifest_name="DOC-1.json")
        _world(tmp_path, node_id="DOC-1@second", manifest_name="DOC-1.second.json")
        assert cp.find_import_manifest(tmp_path, document_id="DOC-1") is None

    def test_a_document_id_with_one_manifest_resolves(self, tmp_path):
        _world(tmp_path)
        found = cp.find_import_manifest(tmp_path, document_id="DOC-1")
        assert found is not None and found.name == "DOC-1.json"

    def test_an_absent_imports_directory_is_not_an_error(self, tmp_path):
        assert cp.find_import_manifest(tmp_path, document_id="DOC-1") is None

    def test_an_unreadable_manifest_beside_a_readable_one_is_skipped(self, tmp_path):
        _world(tmp_path)
        (tmp_path / cp.IMPORT_MANIFESTS_REL / "broken.json").write_text("{", encoding="utf-8")
        found = cp.find_import_manifest(tmp_path, node_id="DOC-1@aaaa")
        assert found is not None and found.name == "DOC-1.json"

    def test_resolving_nothing_yields_an_explicit_gap(self, tmp_path):
        p = cp.resolve_provenance(repo_root=tmp_path, graph_root=tmp_path, node_id="DOC-9@x")
        assert p.grounding_cause == cp.CAUSE_UNSTATED
        assert p.grounding_reason == cp.REASON_UNSTATED
        assert p.sources == ()
        assert any("no import manifest was found for DOC-9@x" in f for f in p.flags)

    def test_a_named_manifest_wins_over_the_search(self, tmp_path):
        manifest = _world(tmp_path, **_REFERENCED)
        p = cp.resolve_provenance(repo_root=tmp_path, manifest_path=manifest, graph_root=tmp_path)
        assert p.grounding_cause == cp.CAUSE_SOURCES_PRESENT

    def test_a_named_manifest_that_is_absent_is_a_refusal(self, tmp_path):
        with pytest.raises(cp.CandidateProvenanceError, match="import manifest not found"):
            cp.resolve_provenance(repo_root=tmp_path, manifest_path=tmp_path / "nope.json")


# --------------------------------------------------------------------------- #
# The real committed records
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not DN_WORKSPACE.is_dir(), reason="the DN workspace is not on this branch")
class TestTheCommittedRecords:
    @pytest.mark.parametrize("node_hex", ["b51a103520b58ded", "bdb8670f6987e4db"])
    def test_both_revisions_derive_the_committed_wording(self, node_hex):
        p = cp.resolve_provenance(
            repo_root=REPO, graph_root=DN_WORKSPACE, node_id=f"{DN_DOCUMENT}@{node_hex}"
        )
        assert p.grounding_cause == cp.CAUSE_SANITISATION
        assert p.grounding_reason == "supporting sources removed by sanitisation"
        assert p.identity_statement == (
            "The identifiers were removed by sanitisation, so the two cannot be compared"
        )
        assert p.expected_ledger_status == "unresolved"
        assert p.flags == ()

    def test_each_revision_reads_its_own_register(self):
        first = cp.resolve_provenance(
            repo_root=REPO, graph_root=DN_WORKSPACE, node_id=f"{DN_DOCUMENT}@bdb8670f6987e4db"
        )
        second = cp.resolve_provenance(
            repo_root=REPO, graph_root=DN_WORKSPACE, node_id=f"{DN_DOCUMENT}@b51a103520b58ded"
        )
        assert first.sources != second.sources
        assert all(Path(REPO / s).is_file() for p in (first, second) for s in p.sources)
