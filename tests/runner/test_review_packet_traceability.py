"""
Tests for proposal-section-traceability-check review_packet_structural_index mode.

Verifies:
1. Audit-mode detection: review_packet.json triggers review_packet_structural_index.
2. Positive fixture: valid review_packet.json passes RP-01 through RP-10.
3. Empty review packet: findings=[] and revision_actions=[] is acceptable.
4. Missing linkage: orphaned finding_id in revision_actions -> RP-07 unresolved.
5. Missing/invalid severity: RP-04/RP-09 unresolved.
6. Missing evidence/recommendation: RP-08 unresolved.
7. No re-audit regression: spec forbids re-auditing sections / re-running evaluator.
8. Runtime integration: n08e accepts review_packet.json artifact_path.
9. Existing modes unchanged: section mode and assembled mode still work.

These are static/spec tests and fixture validation — no live Claude invocations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKILLS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_skill(name: str) -> str:
    path = SKILLS_DIR / name
    assert path.is_file(), f"Skill spec not found: {path}"
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _make_review_packet(
    *,
    run_id: str = "test-run-id",
    schema_id: str = "orch.tier5.review_packet.v1",
    findings: list[dict] | None = None,
    revision_actions: list[dict] | None = None,
    extra_keys: dict | None = None,
) -> dict:
    """Build a minimal valid review_packet.json fixture."""
    default_findings = [
        {
            "finding_id": "F-01",
            "section_id": "excellence",
            "criterion": "Excellence",
            "description": "State-of-the-art analysis is superficial.",
            "severity": "major",
            "evidence": "The proposal states 'we advance beyond state of the art' without specifics.",
            "recommendation": "Add a systematic comparison with named competing approaches.",
        },
        {
            "finding_id": "F-02",
            "section_id": "impact",
            "criterion": "Impact",
            "description": "Impact pathways lack causal chains.",
            "severity": "minor",
            "evidence": "Pathways listed as bullet points without causal logic.",
            "recommendation": "Restructure as Output -> Outcome -> Impact chains.",
        },
    ]
    default_actions = [
        {
            "action_id": "A-1",
            "finding_id": "F-01",
            "priority": 1,
            "action_description": "Expand state-of-the-art comparison.",
            "target_section": "excellence",
            "severity": "major",
        },
        {
            "action_id": "A-2",
            "finding_id": "F-02",
            "priority": 2,
            "action_description": "Restructure impact pathways.",
            "target_section": "impact",
            "severity": "minor",
        },
    ]
    packet: dict[str, Any] = {
        "schema_id": schema_id,
        "run_id": run_id,
        "findings": findings if findings is not None else default_findings,
        "revision_actions": (
            revision_actions if revision_actions is not None else default_actions
        ),
    }
    if extra_keys:
        packet.update(extra_keys)
    return packet


def _simulate_rp_checks(packet: dict, run_id: str = "test-run-id") -> list[dict]:
    """Simulate the RP-01 through RP-10 checks on a review packet dict.

    Returns claim_audit_results list. This mirrors the logic the skill spec
    defines for review_packet_structural_index mode.
    """
    results = []

    # RP-01: valid JSON with correct schema
    rp01_ok = (
        isinstance(packet, dict)
        and packet.get("schema_id") == "orch.tier5.review_packet.v1"
    )
    results.append({
        "claim_id": "RP-01",
        "claim_summary": "Review packet exists, is valid JSON, and has correct schema_id",
        "status": "confirmed" if rp01_ok else "unresolved",
        "source_ref": "review_packet.json:schema_id",
        "flag_reason": None if rp01_ok else "schema_id missing or incorrect",
    })

    # RP-02: run_id present and matches
    rp02_ok = packet.get("run_id") == run_id
    results.append({
        "claim_id": "RP-02",
        "claim_summary": "run_id is present and matches current run_id",
        "status": "confirmed" if rp02_ok else "unresolved",
        "source_ref": "review_packet.json:run_id",
        "flag_reason": None if rp02_ok else "run_id absent or mismatch",
    })

    # RP-03: findings[] exists and is array with required fields
    findings = packet.get("findings")
    rp03_ok = isinstance(findings, list)
    if rp03_ok and len(findings) > 0:
        required_fields = {"finding_id", "section_id", "criterion", "description", "severity", "evidence", "recommendation"}
        for f in findings:
            if not required_fields.issubset(f.keys()):
                rp03_ok = False
                break
    results.append({
        "claim_id": "RP-03",
        "claim_summary": "findings[] exists and is array with required fields",
        "status": "confirmed" if rp03_ok else "unresolved",
        "source_ref": "review_packet.json:findings",
        "flag_reason": None if rp03_ok else "findings missing, not array, or missing required fields",
    })

    # RP-04: Every severity value is valid
    valid_severities = {"critical", "major", "minor"}
    rp04_ok = isinstance(findings, list) and all(
        f.get("severity") in valid_severities for f in findings
    )
    results.append({
        "claim_id": "RP-04",
        "claim_summary": "Every findings[].severity is one of critical/major/minor",
        "status": "confirmed" if rp04_ok else "unresolved",
        "source_ref": "review_packet.json:findings[].severity",
        "flag_reason": None if rp04_ok else "invalid or missing severity value",
    })

    # RP-05: revision_actions[] linkage constraint
    actions = packet.get("revision_actions")
    rp05_ok = isinstance(actions, list)
    if rp05_ok and isinstance(findings, list) and len(findings) > 0:
        rp05_ok = len(actions) > 0
    results.append({
        "claim_id": "RP-05",
        "claim_summary": "revision_actions[] exists; non-empty if findings non-empty",
        "status": "confirmed" if rp05_ok else "unresolved",
        "source_ref": "review_packet.json:revision_actions",
        "flag_reason": None if rp05_ok else "revision_actions empty/missing when findings non-empty",
    })

    # RP-06: Every revision action has required fields
    action_required = {"action_id", "finding_id", "priority", "action_description", "target_section", "severity"}
    rp06_ok = isinstance(actions, list) and all(
        action_required.issubset(a.keys()) for a in actions
    )
    results.append({
        "claim_id": "RP-06",
        "claim_summary": "Every revision_actions[] entry has all required fields",
        "status": "confirmed" if rp06_ok else "unresolved",
        "source_ref": "review_packet.json:revision_actions[]",
        "flag_reason": None if rp06_ok else "missing required fields in revision_actions",
    })

    # RP-07: Every revision_actions[].finding_id references an existing finding
    finding_ids = {f["finding_id"] for f in (findings or []) if "finding_id" in f}
    orphaned = []
    if isinstance(actions, list):
        for a in actions:
            fid = a.get("finding_id")
            if fid not in finding_ids:
                orphaned.append(a.get("action_id", "unknown"))
    rp07_ok = len(orphaned) == 0 and isinstance(actions, list)
    results.append({
        "claim_id": "RP-07",
        "claim_summary": "Every revision_actions[].finding_id references existing finding",
        "status": "confirmed" if rp07_ok else "unresolved",
        "source_ref": "review_packet.json:revision_actions[].finding_id",
        "flag_reason": None if rp07_ok else f"orphaned action_ids: {orphaned}",
    })

    # RP-08: Every finding has non-empty evidence and recommendation
    rp08_ok = isinstance(findings, list) and all(
        bool(f.get("evidence")) and bool(f.get("recommendation"))
        for f in findings
    )
    results.append({
        "claim_id": "RP-08",
        "claim_summary": "Every finding has non-empty evidence and recommendation",
        "status": "confirmed" if rp08_ok else "unresolved",
        "source_ref": "review_packet.json:findings[].evidence/recommendation",
        "flag_reason": None if rp08_ok else "empty evidence or recommendation",
    })

    # RP-09: No finding has severity omitted or outside allowed set (cross-check RP-04)
    rp09_ok = isinstance(findings, list) and all(
        "severity" in f and f["severity"] in valid_severities
        for f in findings
    )
    results.append({
        "claim_id": "RP-09",
        "claim_summary": "No finding has severity omitted or outside allowed set",
        "status": "confirmed" if rp09_ok else "unresolved",
        "source_ref": "review_packet.json:findings[].severity",
        "flag_reason": None if rp09_ok else "severity absent or invalid",
    })

    # RP-10: Review packet does not claim to finalize proposal text
    forbidden_keys = {"finalized_text", "final_draft", "revised_content"}
    rp10_ok = not any(k in packet for k in forbidden_keys)
    results.append({
        "claim_id": "RP-10",
        "claim_summary": "Review packet does not contain finalization keys",
        "status": "confirmed" if rp10_ok else "unresolved",
        "source_ref": "review_packet.json:top-level keys",
        "flag_reason": None if rp10_ok else f"forbidden keys found: {forbidden_keys & set(packet.keys())}",
    })

    return results


# ===========================================================================
# 1. AUDIT-MODE DETECTION
# ===========================================================================


class TestAuditModeDetection:
    """Verify spec recognizes review_packet.json as review_packet_structural_index."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("proposal-section-traceability-check.md")

    def test_review_packet_mode_recognized(self) -> None:
        """Spec must recognize artifact_path ending with review_packet.json."""
        assert "review_packet.json" in self.text
        assert "review_packet_structural_index" in self.text

    def test_review_packet_sets_section_id_audited(self) -> None:
        """Spec must set section_id_audited = 'review_packet'."""
        assert '"review_packet"' in self.text

    def test_review_packet_skips_to_step_2b(self) -> None:
        """Spec must skip to Step 2B for review-packet mode."""
        assert "Step 2B" in self.text
        assert "Do NOT proceed to Steps 1.2–1.5, 2.1–2.6, or 2A" in self.text


# ===========================================================================
# 2. POSITIVE FIXTURE TEST
# ===========================================================================


class TestPositiveReviewPacket:
    """Verify a valid review_packet.json passes all RP checks."""

    def test_valid_packet_passes_all_rp_checks(self) -> None:
        """A well-formed review packet must pass RP-01 through RP-10."""
        packet = _make_review_packet()
        results = _simulate_rp_checks(packet)
        assert len(results) == 10
        for r in results:
            assert r["status"] == "confirmed", (
                f"{r['claim_id']} failed: {r['flag_reason']}"
            )

    def test_valid_packet_no_unsupported_claims_true(self) -> None:
        """All checks confirmed -> no_unsupported_claims_declaration = true."""
        packet = _make_review_packet()
        results = _simulate_rp_checks(packet)
        all_confirmed = all(r["status"] == "confirmed" for r in results)
        assert all_confirmed is True

    def test_valid_packet_written_to_disk(self, tmp_path: Path) -> None:
        """Review packet written on disk should be valid JSON."""
        packet = _make_review_packet()
        path = tmp_path / "review_packets" / "review_packet.json"
        _write_json(path, packet)
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["schema_id"] == "orch.tier5.review_packet.v1"
        assert len(loaded["findings"]) == 2
        assert len(loaded["revision_actions"]) == 2


# ===========================================================================
# 3. EMPTY REVIEW PACKET TEST
# ===========================================================================


class TestEmptyReviewPacket:
    """Verify empty findings[] and revision_actions[] is acceptable."""

    def test_empty_findings_and_actions_pass(self) -> None:
        """If findings=[] and revision_actions=[], all RP checks pass."""
        packet = _make_review_packet(findings=[], revision_actions=[])
        results = _simulate_rp_checks(packet)
        for r in results:
            assert r["status"] == "confirmed", (
                f"{r['claim_id']} failed: {r['flag_reason']}"
            )

    def test_empty_findings_nonempty_actions_still_passes(self) -> None:
        """findings=[] with non-empty revision_actions is structurally valid.

        The spec says revision_actions must be non-empty only if findings
        is non-empty. Extra actions with no findings is unusual but not
        a structural error (RP-07 would catch orphans though).
        """
        packet = _make_review_packet(
            findings=[],
            revision_actions=[{
                "action_id": "A-1",
                "finding_id": "F-99",  # orphaned
                "priority": 1,
                "action_description": "Orphaned action",
                "target_section": "excellence",
                "severity": "minor",
            }],
        )
        results = _simulate_rp_checks(packet)
        # RP-07 should fail because F-99 doesn't exist in findings
        rp07 = next(r for r in results if r["claim_id"] == "RP-07")
        assert rp07["status"] == "unresolved"


# ===========================================================================
# 4. MISSING LINKAGE TEST
# ===========================================================================


class TestMissingLinkage:
    """revision_actions[].finding_id references unknown finding -> RP-07 unresolved."""

    def test_orphaned_finding_id_fails_rp07(self) -> None:
        """An action referencing a non-existent finding_id fails RP-07."""
        packet = _make_review_packet(
            revision_actions=[
                {
                    "action_id": "A-1",
                    "finding_id": "F-01",  # exists
                    "priority": 1,
                    "action_description": "Fix something",
                    "target_section": "excellence",
                    "severity": "major",
                },
                {
                    "action_id": "A-2",
                    "finding_id": "F-NONEXISTENT",  # does NOT exist
                    "priority": 2,
                    "action_description": "Fix something else",
                    "target_section": "impact",
                    "severity": "minor",
                },
            ],
        )
        results = _simulate_rp_checks(packet)
        rp07 = next(r for r in results if r["claim_id"] == "RP-07")
        assert rp07["status"] == "unresolved"
        assert "A-2" in str(rp07["flag_reason"])

    def test_all_linked_passes_rp07(self) -> None:
        """All actions referencing existing findings pass RP-07."""
        packet = _make_review_packet()
        results = _simulate_rp_checks(packet)
        rp07 = next(r for r in results if r["claim_id"] == "RP-07")
        assert rp07["status"] == "confirmed"


# ===========================================================================
# 5. MISSING/INVALID SEVERITY TEST
# ===========================================================================


class TestMissingSeverity:
    """Missing or invalid severity -> RP-04/RP-09 unresolved."""

    def test_invalid_severity_fails_rp04_and_rp09(self) -> None:
        """A finding with severity='high' (invalid) fails RP-04 and RP-09."""
        findings = [
            {
                "finding_id": "F-01",
                "section_id": "excellence",
                "criterion": "Excellence",
                "description": "Bad severity.",
                "severity": "high",  # INVALID
                "evidence": "Some evidence.",
                "recommendation": "Fix it.",
            },
        ]
        packet = _make_review_packet(
            findings=findings,
            revision_actions=[{
                "action_id": "A-1",
                "finding_id": "F-01",
                "priority": 1,
                "action_description": "Fix",
                "target_section": "excellence",
                "severity": "major",
            }],
        )
        results = _simulate_rp_checks(packet)
        rp04 = next(r for r in results if r["claim_id"] == "RP-04")
        rp09 = next(r for r in results if r["claim_id"] == "RP-09")
        assert rp04["status"] == "unresolved"
        assert rp09["status"] == "unresolved"

    def test_missing_severity_field_fails(self) -> None:
        """A finding with no severity key at all fails RP-04 and RP-09."""
        findings = [
            {
                "finding_id": "F-01",
                "section_id": "excellence",
                "criterion": "Excellence",
                "description": "No severity.",
                # "severity" key intentionally omitted
                "evidence": "Evidence here.",
                "recommendation": "Recommend here.",
            },
        ]
        packet = _make_review_packet(
            findings=findings,
            revision_actions=[{
                "action_id": "A-1",
                "finding_id": "F-01",
                "priority": 1,
                "action_description": "Fix",
                "target_section": "excellence",
                "severity": "major",
            }],
        )
        results = _simulate_rp_checks(packet)
        rp04 = next(r for r in results if r["claim_id"] == "RP-04")
        rp09 = next(r for r in results if r["claim_id"] == "RP-09")
        assert rp04["status"] == "unresolved"
        assert rp09["status"] == "unresolved"


# ===========================================================================
# 6. MISSING EVIDENCE/RECOMMENDATION TEST
# ===========================================================================


class TestMissingEvidence:
    """Empty evidence or recommendation -> RP-08 unresolved."""

    def test_empty_evidence_fails_rp08(self) -> None:
        """A finding with empty evidence string fails RP-08."""
        findings = [
            {
                "finding_id": "F-01",
                "section_id": "excellence",
                "criterion": "Excellence",
                "description": "Test.",
                "severity": "major",
                "evidence": "",  # EMPTY
                "recommendation": "Fix it.",
            },
        ]
        packet = _make_review_packet(
            findings=findings,
            revision_actions=[{
                "action_id": "A-1",
                "finding_id": "F-01",
                "priority": 1,
                "action_description": "Fix",
                "target_section": "excellence",
                "severity": "major",
            }],
        )
        results = _simulate_rp_checks(packet)
        rp08 = next(r for r in results if r["claim_id"] == "RP-08")
        assert rp08["status"] == "unresolved"

    def test_empty_recommendation_fails_rp08(self) -> None:
        """A finding with empty recommendation fails RP-08."""
        findings = [
            {
                "finding_id": "F-01",
                "section_id": "excellence",
                "criterion": "Excellence",
                "description": "Test.",
                "severity": "major",
                "evidence": "Some evidence.",
                "recommendation": "",  # EMPTY
            },
        ]
        packet = _make_review_packet(
            findings=findings,
            revision_actions=[{
                "action_id": "A-1",
                "finding_id": "F-01",
                "priority": 1,
                "action_description": "Fix",
                "target_section": "excellence",
                "severity": "major",
            }],
        )
        results = _simulate_rp_checks(packet)
        rp08 = next(r for r in results if r["claim_id"] == "RP-08")
        assert rp08["status"] == "unresolved"

    def test_null_evidence_fails_rp08(self) -> None:
        """A finding with null evidence fails RP-08."""
        findings = [
            {
                "finding_id": "F-01",
                "section_id": "excellence",
                "criterion": "Excellence",
                "description": "Test.",
                "severity": "major",
                "evidence": None,  # NULL
                "recommendation": "Fix it.",
            },
        ]
        packet = _make_review_packet(
            findings=findings,
            revision_actions=[{
                "action_id": "A-1",
                "finding_id": "F-01",
                "priority": 1,
                "action_description": "Fix",
                "target_section": "excellence",
                "severity": "major",
            }],
        )
        results = _simulate_rp_checks(packet)
        rp08 = next(r for r in results if r["claim_id"] == "RP-08")
        assert rp08["status"] == "unresolved"


# ===========================================================================
# 7. NO RE-AUDIT REGRESSION TEST
# ===========================================================================


class TestNoReauditRegression:
    """Spec must explicitly forbid re-auditing sections / re-running evaluator."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("proposal-section-traceability-check.md")

    def test_spec_forbids_reaudit_proposal_sections(self) -> None:
        """Spec must state: do not re-audit proposal sections."""
        # Check both the general assembled-mode MUST NOT and the
        # review-packet-mode MUST NOT
        assert "Do NOT re-audit proposal sections" in self.text

    def test_spec_forbids_rerun_evaluator_review(self) -> None:
        """Spec must state: do not re-run evaluator review."""
        assert "Do NOT re-run evaluator review" in self.text

    def test_spec_declares_review_packet_structural_index(self) -> None:
        """Spec must declare audit_mode = review_packet_structural_index."""
        assert "review_packet_structural_index" in self.text

    def test_spec_does_not_read_section_files_in_rp_mode(self) -> None:
        """Review-packet mode MUST NOT read proposal section files."""
        assert "Read proposal section files or the assembled draft" in self.text

    def test_spec_does_not_extract_claims_in_rp_mode(self) -> None:
        """Review-packet mode MUST NOT extract material claims from content."""
        assert "Do NOT extract material claims from proposal content" in self.text


# ===========================================================================
# 8. RUNTIME INTEGRATION TEST
# ===========================================================================


class TestRuntimeIntegration:
    """For n08e, proposal-section-traceability-check accepts review_packet.json."""

    def test_n08e_fallback_dir_includes_review_packets(self) -> None:
        """agent_runtime._NODE_AUDITABLE_FALLBACK_DIRS for n08e must include
        review_packets directory."""
        from runner.agent_runtime import _NODE_AUDITABLE_FALLBACK_DIRS

        dirs = _NODE_AUDITABLE_FALLBACK_DIRS.get("n08e_evaluator_review")
        assert dirs is not None
        assert any("review_packets" in d for d in dirs)

    def test_resolve_auditable_artifact_finds_review_packet(
        self, tmp_path: Path
    ) -> None:
        """_resolve_auditable_artifact returns review_packet.json path for n08e
        when it exists in all_outputs."""
        from runner.agent_runtime import _resolve_auditable_artifact

        # Simulate: evaluator-criteria-review wrote review_packet.json
        all_outputs = [
            "docs/tier5_deliverables/review_packets/review_packet.json",
        ]
        # The file must exist for fallback, but primary search is all_outputs
        result = _resolve_auditable_artifact(
            "n08e_evaluator_review", all_outputs, tmp_path
        )
        assert result == "docs/tier5_deliverables/review_packets/review_packet.json"

    def test_review_packet_path_matches_spec_mode_detection(self) -> None:
        """The path resolved by the runtime ends with 'review_packet.json',
        which the skill spec recognizes as review-packet mode."""
        path = "docs/tier5_deliverables/review_packets/review_packet.json"
        assert path.endswith("review_packet.json")

    def test_valid_fixture_produces_success_report(self, tmp_path: Path) -> None:
        """A valid review_packet.json should produce a report where all
        RP checks are confirmed — the expected next-run success condition."""
        packet = _make_review_packet()
        results = _simulate_rp_checks(packet)

        # Build the expected report structure
        confirmed_count = sum(1 for r in results if r["status"] == "confirmed")
        unresolved_count = sum(1 for r in results if r["status"] == "unresolved")

        report = {
            "report_id": "traceability_review_packet_evaluator_reviewer_2026-05-03T00:00:00Z",
            "skill_id": "proposal-section-traceability-check",
            "invoking_agent": "evaluator_reviewer",
            "run_id_reference": "test-run-id",
            "section_id_audited": "review_packet",
            "audit_mode": "review_packet_structural_index",
            "claim_audit_results": results,
            "summary": {
                "total_claims": 10,
                "confirmed": confirmed_count,
                "inferred": 0,
                "assumed": 0,
                "unresolved": unresolved_count,
            },
            "no_unsupported_claims_declaration": unresolved_count == 0,
            "timestamp": "2026-05-03T00:00:00Z",
        }

        assert report["summary"]["total_claims"] == 10
        assert report["summary"]["confirmed"] == 10
        assert report["summary"]["unresolved"] == 0
        assert report["no_unsupported_claims_declaration"] is True
        assert report["audit_mode"] == "review_packet_structural_index"
        assert report["section_id_audited"] == "review_packet"


# ===========================================================================
# 9. EXISTING MODES UNCHANGED
# ===========================================================================


class TestExistingModesUnchanged:
    """Verify section mode and assembled mode still recognized."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("proposal-section-traceability-check.md")

    def test_section_mode_still_recognized(self) -> None:
        """excellence_section.json, impact_section.json, implementation_section.json
        must still trigger section mode."""
        assert "excellence_section.json" in self.text
        assert "impact_section.json" in self.text
        assert "implementation_section.json" in self.text
        assert "section mode" in self.text

    def test_assembled_mode_still_recognized(self) -> None:
        """part_b_assembled_draft.json must still trigger assembled mode."""
        assert "part_b_assembled_draft.json" in self.text
        assert "assembled mode" in self.text

    def test_section_mode_material_claim_extraction_intact(self) -> None:
        """Section mode still requires material claim extraction."""
        assert "Material claim extraction" in self.text
        assert "Step 2.2" in self.text

    def test_assembled_mode_assembly_checks_intact(self) -> None:
        """Assembled mode still has ASSEMBLY-01 through ASSEMBLY-08."""
        for i in range(1, 9):
            assert f"ASSEMBLY-{i:02d}" in self.text

    def test_section_mode_does_not_skip_step_14_15(self) -> None:
        """Section mode must still do Steps 1.4, 1.5."""
        assert "Step 1.4 (section mode only)" in self.text
        assert "Step 1.5 (section mode only)" in self.text


# ===========================================================================
# 10. RP-10 FORBIDDEN KEYS TEST
# ===========================================================================


class TestForbiddenKeys:
    """RP-10: review packet must not contain finalization keys."""

    def test_finalized_text_key_fails_rp10(self) -> None:
        """Presence of finalized_text key fails RP-10."""
        packet = _make_review_packet(extra_keys={"finalized_text": "Some text"})
        results = _simulate_rp_checks(packet)
        rp10 = next(r for r in results if r["claim_id"] == "RP-10")
        assert rp10["status"] == "unresolved"

    def test_final_draft_key_fails_rp10(self) -> None:
        """Presence of final_draft key fails RP-10."""
        packet = _make_review_packet(extra_keys={"final_draft": {}})
        results = _simulate_rp_checks(packet)
        rp10 = next(r for r in results if r["claim_id"] == "RP-10")
        assert rp10["status"] == "unresolved"

    def test_revised_content_key_fails_rp10(self) -> None:
        """Presence of revised_content key fails RP-10."""
        packet = _make_review_packet(extra_keys={"revised_content": "text"})
        results = _simulate_rp_checks(packet)
        rp10 = next(r for r in results if r["claim_id"] == "RP-10")
        assert rp10["status"] == "unresolved"

    def test_clean_packet_passes_rp10(self) -> None:
        """No forbidden keys -> RP-10 passes."""
        packet = _make_review_packet()
        results = _simulate_rp_checks(packet)
        rp10 = next(r for r in results if r["claim_id"] == "RP-10")
        assert rp10["status"] == "confirmed"


# ===========================================================================
# 11. SCHEMA MISMATCH TEST
# ===========================================================================


class TestSchemaMismatch:
    """RP-01: wrong schema_id -> unresolved."""

    def test_wrong_schema_fails_rp01(self) -> None:
        """schema_id != 'orch.tier5.review_packet.v1' fails RP-01."""
        packet = _make_review_packet(schema_id="orch.tier5.something_else.v1")
        results = _simulate_rp_checks(packet)
        rp01 = next(r for r in results if r["claim_id"] == "RP-01")
        assert rp01["status"] == "unresolved"

    def test_missing_schema_fails_rp01(self) -> None:
        """Missing schema_id fails RP-01."""
        packet = _make_review_packet()
        del packet["schema_id"]
        results = _simulate_rp_checks(packet)
        rp01 = next(r for r in results if r["claim_id"] == "RP-01")
        assert rp01["status"] == "unresolved"


# ===========================================================================
# 12. RUN_ID MISMATCH TEST
# ===========================================================================


class TestRunIdMismatch:
    """RP-02: run_id mismatch -> unresolved."""

    def test_wrong_run_id_fails_rp02(self) -> None:
        """run_id != current run_id fails RP-02."""
        packet = _make_review_packet(run_id="wrong-run-id")
        results = _simulate_rp_checks(packet, run_id="correct-run-id")
        rp02 = next(r for r in results if r["claim_id"] == "RP-02")
        assert rp02["status"] == "unresolved"

    def test_correct_run_id_passes_rp02(self) -> None:
        """Matching run_id passes RP-02."""
        packet = _make_review_packet(run_id="my-run")
        results = _simulate_rp_checks(packet, run_id="my-run")
        rp02 = next(r for r in results if r["claim_id"] == "RP-02")
        assert rp02["status"] == "confirmed"
