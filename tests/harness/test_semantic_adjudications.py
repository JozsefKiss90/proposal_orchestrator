"""
The R03 semantic adjudication record over the committed MSCA-DN comparison.

The record is hand-authored prose and the prose is the point: a deterministic
comparison can be syntactically correct and still compare two different
relationships, and only a reader settles that.  What a test can do is refuse a
record whose evidence does not hold.  So every check here is a measurement:

* every input the record names is re-hashed on disk;
* every candidate quote resolves against the candidate, through the
  comparison's own resolver;
* every blind and audit reference resolves, and its recorded text is the text
  the artifact holds;
* every application-form quote occurs in the form's own bytes;
* every register pointer resolves;
* the observation ids are the ESR record's, and they cover every row the R02
  review handed to R03;
* the vocabularies are the ones the record documents, the statuses are the
  comparison module's own four, and a row whose reading is unresolved names a
  decision;
* the finding figures the record states are the figures the two audit reports
  hold.

Nothing here judges an interpretation.  That is the operator's.
"""
from __future__ import annotations

import json
import re

import pytest

import harness.integrity_audit as ia
from harness.blind_assessment import candidate_hash, load_candidate
from harness.esr_comparison import (
    DECLARED_STATUSES,
    load_audits,
    resolve_audit_reference,
    resolve_blind_reference,
    resolve_register_pointer,
    verify_evidence,
)
from harness.evidence_preflight import file_sha256
from harness.profile import load_profile
from runner.paths import find_repo_root
from tests.harness.test_esr_comparison import DN_PROFILE  # noqa: F401 - the DN profile path

REPO = find_repo_root()
RECORD_PATH = (
    REPO / "docs/tier4_orchestration_state/msca_dn/esr/semantic_adjudications_f60ae6e0a2a1.json"
)

#: The five classes the ticket names, plus the two the record adds and explains.
CLASSIFICATIONS = (
    "actual_inconsistency",
    "ambiguous_relationship",
    "extraction_issue",
    "sanitisation_limitation",
    "unsupported_checker_assumption",
    "unsupported_lane_claim",
    "dispute_not_sustained",
)
FAILURE_MODES = (
    "evidence_not_read",
    "evidence_read_and_rated_adequate",
    "evidence_read_and_misattributed",
    "evidence_read_but_not_interrogated",
    "not_applicable",
)

#: The rows the R02 review handed to R03 (recommendation ``revisit_in_r03``).
HANDED_OVER = (
    "ESR-E-03", "ESR-E-04", "ESR-E-07", "ESR-E-09", "ESR-Q-01", "ESR-Q-02", "ESR-Q-03",
)

pytestmark = pytest.mark.skipif(
    not RECORD_PATH.is_file(), reason="MSCA-DN adjudication record not on this branch"
)


@pytest.fixture(scope="module")
def record() -> dict:
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def candidate(record):
    return load_candidate(REPO / record["candidate"], load_profile(DN_PROFILE))


@pytest.fixture(scope="module")
def baseline(record) -> dict:
    return json.loads((REPO / record["baseline_report"]).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def audits(record):
    return load_audits(
        [entry["path"] for entry in record["audits"].values()], repo_root=REPO
    )


@pytest.fixture(scope="module")
def register(record) -> dict:
    return json.loads((REPO / record["fidelity_register"]).read_text(encoding="utf-8"))


def _evidence(record) -> list[tuple[str, dict]]:
    """Every evidence entry, labelled by the adjudication and half it sits in."""
    out: list[tuple[str, dict]] = []
    for row in record["adjudications"]:
        for half in ("measured", "interpretation"):
            for item in row[half].get("evidence") or []:
                out.append((f"{row['adjudication_id']}/{half}", item))
    return out


class TestTheRecordItself:
    def test_it_is_advisory_and_claims_no_approval(self, record):
        assert record["record_type"] == "esr_semantic_adjudications"
        assert record["advisory"] is True and record["blocking"] is False
        assert record["review_state"] == "agent_drafted_pending_operator_review"
        assert "provisional" in record["declared_by"]

    @pytest.mark.parametrize(
        "path_key,hash_key",
        [
            ("comparison", "comparison_sha256"),
            ("esr_record", "esr_record_sha256"),
            ("dispositions", "dispositions_sha256"),
            ("baseline_report", "baseline_report_sha256"),
            ("fidelity_register", "fidelity_register_sha256"),
            ("tier2a_application_form", "tier2a_application_form_sha256"),
        ],
    )
    def test_every_named_input_rehashes(self, record, path_key, hash_key):
        assert file_sha256(REPO / record[path_key]) == record[hash_key]

    def test_every_audit_rehashes(self, record):
        for role, entry in record["audits"].items():
            assert file_sha256(REPO / entry["path"]) == entry["sha256"], role

    def test_the_candidate_hash_is_the_candidates_own(self, record, candidate):
        assert candidate_hash(candidate) == record["candidate_hash"]

    def test_the_classification_note_names_every_value_used(self, record):
        note = record["classification_note"]
        used = {row["classification"] for row in record["adjudications"]}
        assert used <= set(CLASSIFICATIONS)
        for value in used:
            assert value in note, value

    def test_the_failure_mode_note_names_every_value_used(self, record):
        note = record["failure_mode_note"]
        used = {row["failure_mode"] for row in record["adjudications"]}
        assert used <= set(FAILURE_MODES)
        for value in used:
            if value != "not_applicable":
                assert value in note, value


class TestCoverage:
    def test_every_row_handed_over_by_r02_is_adjudicated(self, record):
        named = {oid for row in record["adjudications"] for oid in row["observation_ids"]}
        assert set(HANDED_OVER) <= named, sorted(set(HANDED_OVER) - named)

    def test_no_observation_id_is_unknown_to_the_esr_record(self, record):
        esr = json.loads((REPO / record["esr_record"]).read_text(encoding="utf-8"))
        known = {str(o["id"]) for o in esr["observations"]}
        named = {oid for row in record["adjudications"] for oid in row["observation_ids"]}
        assert named <= known, sorted(named - known)

    def test_the_adjudication_ids_are_unique_and_ordered(self, record):
        ids = [row["adjudication_id"] for row in record["adjudications"]]
        assert ids == sorted(ids) and len(set(ids)) == len(ids)

    def test_every_row_states_a_measurement_and_a_reading_with_statuses(self, record):
        for row in record["adjudications"]:
            label = row["adjudication_id"]
            for half in ("measured", "interpretation"):
                assert row[half]["statement"].strip(), f"{label}/{half}"
                assert row[half]["status"] in DECLARED_STATUSES, f"{label}/{half}"

    def test_an_unresolved_reading_names_a_decision(self, record):
        """The ticket's criterion: a disputed relationship has an explicit
        interpretation or an unresolved status. An unresolved one must hand the
        operator a question rather than leave the row hanging."""
        for row in record["adjudications"]:
            if row["interpretation"]["status"] == "Unresolved":
                assert (row.get("operator_decision") or "").strip(), row["adjudication_id"]

    def test_the_rows_needing_the_original_are_named_and_not_imported(self, record):
        assert record["requires_the_original"]
        for item in record["requires_the_original"]:
            assert re.search(r"ESR-[EIQ]-\d\d", item), item


class TestEveryReferenceResolves:
    def test_candidate_quotes(self, record, candidate):
        for label, item in _evidence(record):
            if item["source"] != "candidate":
                continue
            verify_evidence(
                candidate,
                {k: item[k] for k in ("section_id", "sub_section_id", "quote")},
                label=label,
            )

    def test_blind_references_and_their_recorded_text(self, record, baseline):
        seen = 0
        for label, item in _evidence(record):
            if item["source"] != "blind_finding":
                continue
            seen += 1
            resolved = resolve_blind_reference(baseline, item, label=label)
            if "text" in item:
                assert resolved["text"] == item["text"], label
            else:
                assert item["text_contains"] in resolved["text"], label
        assert seen >= 6

    def test_audit_references_and_their_recorded_text(self, record, audits):
        seen = 0
        for label, item in _evidence(record):
            if item["source"] != "audit_finding":
                continue
            seen += 1
            resolved = resolve_audit_reference(audits, item, label=label)
            assert resolved["text"] == item["text"], label
        assert seen >= 5

    def test_register_pointers(self, record, register):
        for label, item in _evidence(record):
            if item["source"] != "fidelity_register":
                continue
            resolve_register_pointer(register, item["pointer"], label=label)

    def test_application_form_quotes_occur_in_the_forms_own_bytes(self, record):
        """The form is an RTF, so a quote is checked against the stored bytes.

        A column header is one literal run there; a sentence split across runs
        is not quotable and none is quoted.
        """
        raw = (REPO / record["tier2a_application_form"]).read_bytes().decode("latin-1")
        seen = 0
        for label, item in _evidence(record):
            if item["source"] != "tier2a_application_form":
                continue
            seen += 1
            assert item["quote"] in raw, f"{label}: {item['quote']!r}"
            assert item["locator"].strip(), label
        assert seen >= 5

    def test_every_evidence_source_is_one_the_record_can_resolve(self, record):
        allowed = {
            "candidate", "blind_finding", "audit_finding", "fidelity_register",
            "tier2a_application_form", "measurement",
        }
        for label, item in _evidence(record):
            assert item["source"] in allowed, f"{label}: {item['source']}"
            if item["source"] == "measurement":
                assert item["statement"].strip(), label


class TestTheAuditEffectItStates:
    def test_the_figures_are_the_reports_own(self, record):
        effect = record["audit_effect"]
        cited = json.loads(
            (REPO / record["audits"]["cited_by_the_dispositions"]["path"]).read_text(encoding="utf-8")
        )
        successor = json.loads(
            (REPO / record["audits"]["successor"]["path"]).read_text(encoding="utf-8")
        )
        assert cited["findings_total"] == effect["cited_report_findings"]
        assert successor["findings_total"] == effect["successor_findings"]
        assert effect["added"] == "none"

    def test_the_successor_is_bound_to_the_same_candidate_and_snapshot(self, record):
        cited = json.loads(
            (REPO / record["audits"]["cited_by_the_dispositions"]["path"]).read_text(encoding="utf-8")
        )
        successor = json.loads(
            (REPO / record["audits"]["successor"]["path"]).read_text(encoding="utf-8")
        )
        assert successor["candidate_hash"] == cited["candidate_hash"] == record["candidate_hash"]
        assert successor["snapshot_id"] == cited["snapshot_id"]
        assert successor["baseline"]["status"] == ia.BASELINE_BOUND

    def test_the_removed_findings_are_the_ones_the_record_names(self, record):
        cited = json.loads(
            (REPO / record["audits"]["cited_by_the_dispositions"]["path"]).read_text(encoding="utf-8")
        )
        successor = json.loads(
            (REPO / record["audits"]["successor"]["path"]).read_text(encoding="utf-8")
        )
        before = {(f["kind"], f["subject"]) for c in cited["checks"] for f in c["findings"]}
        after = {(f["kind"], f["subject"]) for c in successor["checks"] for f in c["findings"]}
        gone = before - after
        assert gone == {(ia.KIND_OUT_OF_WINDOW, f"DC{n}") for n in range(1, 10)} | {
            (ia.KIND_INCONSISTENCY, "WP6"), (ia.KIND_INCONSISTENCY, "WP7")
        }
        assert not after - before

    def test_every_code_change_names_its_adjudication_and_its_tests(self, record):
        ids = {row["adjudication_id"] for row in record["adjudications"]}
        for change in record["code_changes"]:
            assert change["adjudication_id"] in ids, change["component"]
            assert change["tests"], change["component"]
            for test_id in change["tests"]:
                path, _, name = test_id.partition("::")
                assert (REPO / path).is_file(), test_id
                assert name.split("::")[-1] in (REPO / path).read_text(encoding="utf-8"), test_id
