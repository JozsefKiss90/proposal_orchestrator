"""
Unit tests for Step 11 (corrected) — runner/semantic_dispatch.py.

The corrected implementation replaces local violation-marker handlers
with open-ended agent invocation via the Claude runtime transport.
These tests mock ``invoke_claude_text`` so no real CLI calls are made.

Test groups:
  - validate_semantic_result       — §4.9 schema validation (unchanged)
  - SemanticRegistry               — configuration correctness
  - InvokeAgentSuccessPath         — pass/fail results correctly integrated
  - InvokeAgentArtifactReading     — disk reads, dir enumeration, run_id sub
  - InvokeAgentResponseParsing     — JSON extraction from various response forms
  - InvokeAgentErrorHandling       — transport errors, malformed responses, unknown fn
  - AgentPromptConstruction        — system/user prompt content verified
  - DispatchSemanticPredicateRouting — public entry point delegates to invoke_agent
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from runner.claude_transport import ClaudeTransportError
from runner.semantic_dispatch import (
    AGENT_MODEL,
    REQUIRED_RESULT_FIELDS,
    SEMANTIC_REGISTRY,
    SemanticPredicateConfig,
    VALID_SEVERITIES,
    dispatch_semantic_predicate,
    invoke_agent,
    validate_semantic_result,
    _build_system_prompt,
    _build_user_prompt,
    _extract_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, content: Any) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(content), encoding="utf-8")
    return p


def _valid_pass_result(pred_id: str = "p01") -> dict:
    return {
        "predicate_id": pred_id,
        "function": "no_unsupported_tier5_claims",
        "status": "pass",
        "agent": "constitutional_compliance_check",
        "constitutional_rule": "CLAUDE.md §13.3",
        "artifacts_inspected": ["/some/path"],
        "findings": [],
        "fail_message": "",
    }


def _valid_fail_result(pred_id: str = "p01") -> dict:
    return {
        "predicate_id": pred_id,
        "function": "no_unsupported_tier5_claims",
        "status": "fail",
        "agent": "constitutional_compliance_check",
        "constitutional_rule": "CLAUDE.md §13.3",
        "artifacts_inspected": ["/some/path"],
        "findings": [
            {
                "claim": "Partner X named without Tier 3 evidence",
                "violated_rule": "CLAUDE.md §13.3",
                "evidence_path": "/docs/tier5/section_a.json",
                "severity": "critical",
            }
        ],
        "fail_message": "1 unsupported claim found.",
    }


def _pred_entry(
    func: str,
    pred_id: str = "p_sem_01",
    args: dict | None = None,
) -> dict:
    return {
        "predicate_id": pred_id,
        "type": "semantic",
        "function": func,
        "args": args or {},
        "prose_condition": "Test condition",
        "fail_message": "Test failure",
    }


def _mock_transport_response(mock_transport: MagicMock, payload: dict) -> None:
    """Configure *mock_transport* to return *payload* as JSON text."""
    mock_transport.return_value = json.dumps(payload)


# ---------------------------------------------------------------------------
# Fixture: mock the Claude runtime transport
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_transport():
    """
    Patch ``runner.semantic_dispatch.invoke_claude_text`` so no real
    CLI calls happen.

    Yields the mock function.  Tests set ``mock_transport.return_value``
    to control responses.
    """
    with patch("runner.semantic_dispatch.invoke_claude_text") as mock_fn:
        yield mock_fn


# ---------------------------------------------------------------------------
# validate_semantic_result — valid inputs  (§4.9, unchanged)
# ---------------------------------------------------------------------------


class TestValidateSemanticResultValid:
    def test_valid_pass_result_accepted(self) -> None:
        ok, err = validate_semantic_result(_valid_pass_result())
        assert ok
        assert err == ""

    def test_valid_fail_result_accepted(self) -> None:
        ok, err = validate_semantic_result(_valid_fail_result())
        assert ok
        assert err == ""

    def test_empty_findings_list_valid_for_pass(self) -> None:
        result = _valid_pass_result()
        result["findings"] = []
        ok, _ = validate_semantic_result(result)
        assert ok

    def test_multiple_findings_valid(self) -> None:
        result = _valid_fail_result()
        result["findings"].append(
            {
                "claim": "Another claim",
                "violated_rule": "CLAUDE.md §11.4",
                "evidence_path": "/docs/tier5/section_b.json",
                "severity": "major",
            }
        )
        ok, _ = validate_semantic_result(result)
        assert ok


# ---------------------------------------------------------------------------
# validate_semantic_result — invalid inputs
# ---------------------------------------------------------------------------


class TestValidateSemanticResultInvalid:
    def test_non_dict_input_rejected(self) -> None:
        ok, err = validate_semantic_result("not a dict")
        assert not ok
        assert "dict" in err

    def test_missing_required_field_rejected(self) -> None:
        result = _valid_pass_result()
        del result["constitutional_rule"]
        ok, err = validate_semantic_result(result)
        assert not ok
        assert "constitutional_rule" in err

    def test_invalid_status_rejected(self) -> None:
        result = _valid_pass_result()
        result["status"] = "pending"
        ok, err = validate_semantic_result(result)
        assert not ok
        assert "status" in err
        assert "pending" in err

    def test_error_status_rejected(self) -> None:
        result = _valid_pass_result()
        result["status"] = "error"
        ok, err = validate_semantic_result(result)
        assert not ok

    def test_findings_not_list_rejected(self) -> None:
        result = _valid_pass_result()
        result["findings"] = "not a list"
        ok, err = validate_semantic_result(result)
        assert not ok
        assert "findings" in err

    def test_finding_missing_violated_rule_rejected(self) -> None:
        result = _valid_fail_result()
        del result["findings"][0]["violated_rule"]
        ok, err = validate_semantic_result(result)
        assert not ok
        assert "violated_rule" in err

    def test_finding_missing_evidence_path_rejected(self) -> None:
        result = _valid_fail_result()
        del result["findings"][0]["evidence_path"]
        ok, err = validate_semantic_result(result)
        assert not ok
        assert "evidence_path" in err

    def test_finding_missing_claim_rejected(self) -> None:
        result = _valid_fail_result()
        del result["findings"][0]["claim"]
        ok, err = validate_semantic_result(result)
        assert not ok
        assert "claim" in err

    def test_finding_blank_violated_rule_rejected(self) -> None:
        result = _valid_fail_result()
        result["findings"][0]["violated_rule"] = "   "
        ok, err = validate_semantic_result(result)
        assert not ok
        assert "violated_rule" in err

    def test_finding_blank_evidence_path_rejected(self) -> None:
        result = _valid_fail_result()
        result["findings"][0]["evidence_path"] = ""
        ok, err = validate_semantic_result(result)
        assert not ok
        assert "evidence_path" in err

    def test_finding_invalid_severity_rejected(self) -> None:
        result = _valid_fail_result()
        result["findings"][0]["severity"] = "low"
        ok, err = validate_semantic_result(result)
        assert not ok
        assert "severity" in err

    def test_finding_non_dict_entry_rejected(self) -> None:
        result = _valid_fail_result()
        result["findings"][0] = "string not dict"
        ok, err = validate_semantic_result(result)
        assert not ok

    def test_missing_predicate_id_rejected(self) -> None:
        result = _valid_pass_result()
        del result["predicate_id"]
        ok, err = validate_semantic_result(result)
        assert not ok
        assert "predicate_id" in err


# ---------------------------------------------------------------------------
# SemanticRegistry — configuration correctness
# ---------------------------------------------------------------------------


class TestSemanticRegistry:
    def test_registry_contains_all_seven_predicates(self) -> None:
        expected = {
            "no_unresolved_scope_conflicts",
            "no_cross_tier_contradictions",
            "no_unsupported_tier5_claims",
            "no_budget_gate_contradiction",
            "no_higher_tier_contradiction",
            "no_forbidden_schema_authority",
            "no_gap_masked_as_confirmed",
        }
        assert expected == set(SEMANTIC_REGISTRY.keys())

    def test_all_entries_are_semantic_predicate_config(self) -> None:
        for name, entry in SEMANTIC_REGISTRY.items():
            assert isinstance(entry, SemanticPredicateConfig), (
                f"{name!r} is not a SemanticPredicateConfig"
            )

    def test_each_entry_has_non_empty_agent(self) -> None:
        for name, entry in SEMANTIC_REGISTRY.items():
            assert entry.agent, f"{name!r} has empty agent"

    def test_each_entry_has_constitutional_rule_referencing_claude_md(self) -> None:
        for name, entry in SEMANTIC_REGISTRY.items():
            assert "CLAUDE.md" in entry.constitutional_rule, (
                f"{name!r} constitutional_rule does not reference CLAUDE.md"
            )

    def test_each_entry_has_non_empty_description(self) -> None:
        for name, entry in SEMANTIC_REGISTRY.items():
            assert entry.description, f"{name!r} has empty description"

    def test_function_field_matches_registry_key(self) -> None:
        for key, entry in SEMANTIC_REGISTRY.items():
            assert entry.function == key, (
                f"function {entry.function!r} does not match registry key {key!r}"
            )


# ---------------------------------------------------------------------------
# InvokeAgentSuccessPath — valid pass/fail responses
# ---------------------------------------------------------------------------


class TestInvokeAgentSuccessPath:
    def test_pass_result_returned_and_passes_validation(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        payload = _valid_pass_result("p_test")
        _mock_transport_response(mock_transport, payload)

        entry = _pred_entry("no_unsupported_tier5_claims", pred_id="p_test")
        result = invoke_agent(entry, "run-1", tmp_path)
        ok, err = validate_semantic_result(result)
        assert ok, err
        assert result["status"] == "pass"

    def test_fail_result_returned_and_passes_validation(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        payload = _valid_fail_result("p_test")
        _mock_transport_response(mock_transport, payload)

        entry = _pred_entry("no_unsupported_tier5_claims", pred_id="p_test")
        result = invoke_agent(entry, "run-1", tmp_path)
        ok, err = validate_semantic_result(result)
        assert ok, err
        assert result["status"] == "fail"
        assert len(result["findings"]) == 1

    def test_predicate_id_always_injected_from_entry(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """Runner injects its own pred_id even if agent sets a different value."""
        payload = _valid_pass_result("wrong_id_from_agent")
        _mock_transport_response(mock_transport, payload)

        entry = _pred_entry("no_forbidden_schema_authority", pred_id="authoritative_id")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result["predicate_id"] == "authoritative_id"

    def test_artifacts_inspected_set_from_disk_not_agent(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """artifacts_inspected reflects what was actually read, overriding agent."""
        art = tmp_path / "section.json"
        art.write_text('{"title": "Section A"}', encoding="utf-8")

        payload = _valid_pass_result()
        payload["artifacts_inspected"] = ["/agent/self/report"]  # agent's value
        _mock_transport_response(mock_transport, payload)

        entry = _pred_entry(
            "no_gap_masked_as_confirmed",
            args={"sections_path": str(art)},
        )
        result = invoke_agent(entry, "run-1", tmp_path)
        # Must use disk ground truth, not agent's self-report
        assert str(art) in result["artifacts_inspected"]
        assert "/agent/self/report" not in result["artifacts_inspected"]

    def test_findings_from_agent_preserved_in_result(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        payload = _valid_fail_result()
        payload["findings"][0]["claim"] = "Specific violation text"
        _mock_transport_response(mock_transport, payload)

        entry = _pred_entry("no_cross_tier_contradictions")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result["findings"][0]["claim"] == "Specific violation text"

    def test_transport_called_with_correct_model(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        _mock_transport_response(mock_transport, _valid_pass_result())

        entry = _pred_entry("no_unsupported_tier5_claims")
        invoke_agent(entry, "run-1", tmp_path)

        call_kwargs = mock_transport.call_args.kwargs
        assert call_kwargs["model"] == AGENT_MODEL


# ---------------------------------------------------------------------------
# InvokeAgentArtifactReading — disk reads and path resolution
# ---------------------------------------------------------------------------


class TestInvokeAgentArtifactReading:
    def test_file_artifact_content_sent_to_agent(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """The content of the artifact file appears in the user prompt."""
        art = tmp_path / "concept.json"
        art.write_text('{"scope_conflicts": []}', encoding="utf-8")
        scope = tmp_path / "scope.json"
        scope.write_text('{}', encoding="utf-8")

        _mock_transport_response(mock_transport, _valid_pass_result())
        entry = _pred_entry(
            "no_unresolved_scope_conflicts",
            args={"phase2_path": str(art), "scope_path": str(scope)},
        )
        invoke_agent(entry, "run-1", tmp_path)

        user_prompt = mock_transport.call_args.kwargs["user_prompt"]
        assert "scope_conflicts" in user_prompt

    def test_directory_artifacts_enumerate_json_files(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """All .json files in a directory arg are read and sent to the agent."""
        sections = tmp_path / "sections"
        sections.mkdir()
        (sections / "part_b.json").write_text('{"title": "B"}', encoding="utf-8")
        (sections / "part_c.json").write_text('{"title": "C"}', encoding="utf-8")
        (sections / "notes.txt").write_text("ignore me", encoding="utf-8")

        _mock_transport_response(mock_transport, _valid_pass_result())
        entry = _pred_entry(
            "no_forbidden_schema_authority",
            args={"sections_path": str(sections)},
        )
        result = invoke_agent(entry, "run-1", tmp_path)

        # Both JSON files must appear in artifacts_inspected
        assert any("part_b.json" in p for p in result["artifacts_inspected"])
        assert any("part_c.json" in p for p in result["artifacts_inspected"])
        # Non-JSON file must not appear
        assert not any("notes.txt" in p for p in result["artifacts_inspected"])

    def test_nonexistent_path_skipped_gracefully(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """A missing artifact path is silently skipped; no exception raised."""
        _mock_transport_response(mock_transport, _valid_pass_result())
        entry = _pred_entry(
            "no_gap_masked_as_confirmed",
            args={"sections_path": "nonexistent/dir"},
        )
        result = invoke_agent(entry, "run-1", tmp_path)
        # Should still return a result (not raise)
        assert "status" in result

    def test_run_id_substituted_before_path_resolution(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """${run_id} in an arg is replaced with the actual run_id."""
        run_id = "abc-123"
        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "section.json").write_text('{}', encoding="utf-8")

        _mock_transport_response(mock_transport, _valid_pass_result())
        entry = _pred_entry(
            "no_forbidden_schema_authority",
            args={"sections_path": "runs/${run_id}"},
        )
        result = invoke_agent(entry, run_id, tmp_path)
        assert any(run_id in p for p in result["artifacts_inspected"])

    def test_artifact_content_appears_in_user_prompt(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """The user message passed to the transport contains the artifact file content."""
        art = tmp_path / "s.json"
        art.write_text('{"unique_token": "XYZZY42"}', encoding="utf-8")

        _mock_transport_response(mock_transport, _valid_pass_result())
        entry = _pred_entry(
            "no_gap_masked_as_confirmed",
            args={"sections_path": str(art)},
        )
        invoke_agent(entry, "run-1", tmp_path)

        user_prompt = mock_transport.call_args.kwargs["user_prompt"]
        assert "XYZZY42" in user_prompt


# ---------------------------------------------------------------------------
# InvokeAgentResponseParsing — JSON extraction
# ---------------------------------------------------------------------------


class TestInvokeAgentResponseParsing:
    def test_bare_json_response_parsed(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        mock_transport.return_value = json.dumps(_valid_pass_result())

        entry = _pred_entry("no_unsupported_tier5_claims")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result["status"] == "pass"

    def test_json_embedded_in_prose_extracted(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        payload = _valid_pass_result()
        mock_transport.return_value = (
            "Here is my evaluation:\n" + json.dumps(payload) + "\nEnd."
        )

        entry = _pred_entry("no_unsupported_tier5_claims")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result["status"] == "pass"

    def test_json_in_markdown_code_block_extracted(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        payload = _valid_pass_result()
        mock_transport.return_value = "```json\n" + json.dumps(payload) + "\n```"

        entry = _pred_entry("no_unsupported_tier5_claims")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result["status"] == "pass"

    def test_non_json_response_produces_dispatch_error(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        mock_transport.return_value = "I cannot evaluate this predicate."

        entry = _pred_entry("no_unsupported_tier5_claims")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result.get("_dispatch_error") is True
        ok, err = validate_semantic_result(result)
        assert ok, f"Dispatch error should now pass validation: {err}"
        assert result["status"] == "fail"
        assert result["agent"] == "constitutional_compliance_check"

    def test_json_list_response_produces_dispatch_error(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """A JSON array (not object) cannot satisfy the §4.9 schema."""
        mock_transport.return_value = json.dumps([{"status": "pass"}])

        entry = _pred_entry("no_unsupported_tier5_claims")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result.get("_dispatch_error") is True


# ---------------------------------------------------------------------------
# InvokeAgentErrorHandling — transport failures and unknown functions
# ---------------------------------------------------------------------------


class TestInvokeAgentErrorHandling:
    def test_transport_error_produces_dispatch_error(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        mock_transport.side_effect = ClaudeTransportError("network error")

        entry = _pred_entry("no_unsupported_tier5_claims")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result.get("_dispatch_error") is True
        assert "network error" in result.get("_dispatch_error_reason", "")

    def test_dispatch_error_has_dispatch_error_flag(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        mock_transport.side_effect = ClaudeTransportError("timeout")
        entry = _pred_entry("no_forbidden_schema_authority")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result["_dispatch_error"] is True

    def test_dispatch_error_passes_validation_with_fail_status(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        mock_transport.side_effect = ClaudeTransportError("bad")
        entry = _pred_entry("no_forbidden_schema_authority")
        result = invoke_agent(entry, "run-1", tmp_path)
        ok, err = validate_semantic_result(result)
        assert ok, f"Dispatch error should now pass validation: {err}"
        assert result["status"] == "fail"
        assert result["_dispatch_error"] is True
        assert result["agent"] == "constitutional_compliance_check"
        assert result["constitutional_rule"] == "CLAUDE.md §13.1"

    def test_unknown_function_returns_dispatch_error_without_transport_call(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """Unknown function → error before transport is even called."""
        entry = _pred_entry("nonexistent_agent_check")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result.get("_dispatch_error") is True
        mock_transport.assert_not_called()

    def test_unknown_function_reason_names_available_functions(
        self, tmp_path: Path
    ) -> None:
        entry = _pred_entry("mystery_check")
        result = invoke_agent(entry, "run-1", tmp_path)
        reason = result.get("_dispatch_error_reason", "")
        # Should mention at least one known function name
        assert "no_forbidden_schema_authority" in reason

    def test_transport_error_includes_agent_and_constitutional_rule(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """Transport error result includes config fields from SEMANTIC_REGISTRY."""
        mock_transport.side_effect = ClaudeTransportError("network error")
        entry = _pred_entry("no_unresolved_scope_conflicts")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result["agent"] == "concept_refiner"
        assert result["constitutional_rule"] == "CLAUDE.md §7 Phase 2 gate"
        assert result["_dispatch_error_category"] == "TRANSPORT_FAILURE"

    def test_unknown_function_uses_fallback_agent_and_rule(
        self, tmp_path: Path
    ) -> None:
        """Unknown function → fallback agent/rule defaults, still schema-valid."""
        entry = _pred_entry("nonexistent_agent_check")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result["agent"] == "<unknown>"
        assert result["constitutional_rule"] == "<unknown>"
        assert result["_dispatch_error_category"] == "UNKNOWN_FUNCTION"
        ok, err = validate_semantic_result(result)
        assert ok, f"Unknown function dispatch error should pass validation: {err}"

    def test_transport_error_writes_diagnostic_bundle(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """Transport failure writes diagnostic meta to .claude/semantic_diag/."""
        mock_transport.side_effect = ClaudeTransportError("connection reset")
        entry = _pred_entry(
            "no_forbidden_schema_authority",
            args={"sections_path": "missing/dir"},
        )
        result = invoke_agent(entry, "run-abcd1234", tmp_path)
        diag_path = result.get("_diagnostic_bundle_path")
        assert diag_path is not None
        full_path = tmp_path / diag_path
        assert full_path.exists(), f"Diagnostic meta not found at {full_path}"
        meta = json.loads(full_path.read_text(encoding="utf-8"))
        assert meta["category"] == "TRANSPORT_FAILURE"
        assert meta["function"] == "no_forbidden_schema_authority"

    def test_non_json_response_writes_diagnostic_bundle(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """Non-JSON response writes diagnostic bundle with response text."""
        mock_transport.return_value = "Not JSON at all"
        entry = _pred_entry("no_gap_masked_as_confirmed")
        result = invoke_agent(entry, "run-abcd1234", tmp_path)
        diag_path = result.get("_diagnostic_bundle_path")
        assert diag_path is not None
        meta = json.loads((tmp_path / diag_path).read_text(encoding="utf-8"))
        assert meta["category"] == "MALFORMED_RESPONSE"
        # Response text should also be written
        response_files = list(
            (tmp_path / ".claude" / "semantic_diag").glob("*_response.txt")
        )
        assert len(response_files) >= 1

    def test_dispatch_error_has_descriptive_fail_message(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        mock_transport.side_effect = ClaudeTransportError(
            "CLI exited with code 1"
        )
        entry = _pred_entry("no_forbidden_schema_authority")
        result = invoke_agent(entry, "run-1", tmp_path)
        assert result["fail_message"].startswith("Dispatch error:")
        assert "CLI exited with code 1" in result["fail_message"]


# ---------------------------------------------------------------------------
# AgentPromptConstruction — system and user prompt content
# ---------------------------------------------------------------------------


class TestAgentPromptConstruction:
    def test_system_prompt_contains_constitutional_rule(self) -> None:
        config = SEMANTIC_REGISTRY["no_unsupported_tier5_claims"]
        prompt = _build_system_prompt(config)
        assert "CLAUDE.md §13.3" in prompt

    def test_system_prompt_contains_agent_name(self) -> None:
        config = SEMANTIC_REGISTRY["no_cross_tier_contradictions"]
        prompt = _build_system_prompt(config)
        assert "constitutional_compliance_check" in prompt

    def test_system_prompt_contains_function_name(self) -> None:
        config = SEMANTIC_REGISTRY["no_forbidden_schema_authority"]
        prompt = _build_system_prompt(config)
        assert "no_forbidden_schema_authority" in prompt

    def test_system_prompt_contains_result_schema_fields(self) -> None:
        config = SEMANTIC_REGISTRY["no_gap_masked_as_confirmed"]
        prompt = _build_system_prompt(config)
        for field in ("status", "findings", "violated_rule", "evidence_path", "severity"):
            assert field in prompt, f"system prompt missing schema field {field!r}"

    def test_system_prompt_instructs_no_invention(self) -> None:
        config = SEMANTIC_REGISTRY["no_unsupported_tier5_claims"]
        prompt = _build_system_prompt(config)
        # Must instruct agent not to invent violations
        assert "Do NOT invent" in prompt

    def test_user_prompt_contains_artifact_content(self, tmp_path: Path) -> None:
        art = tmp_path / "section.json"
        art.write_text('{"unique_token": "XYZZY99"}', encoding="utf-8")
        config = SEMANTIC_REGISTRY["no_forbidden_schema_authority"]
        contents = {str(art): '{"unique_token": "XYZZY99"}'}
        prompt = _build_user_prompt(config, contents, {})
        assert "XYZZY99" in prompt

    def test_user_prompt_contains_artifact_path(self, tmp_path: Path) -> None:
        art = tmp_path / "myartifact.json"
        art.write_text("{}", encoding="utf-8")
        config = SEMANTIC_REGISTRY["no_forbidden_schema_authority"]
        contents = {str(art): "{}"}
        prompt = _build_user_prompt(config, contents, {})
        assert "myartifact.json" in prompt

    def test_user_prompt_mentions_no_artifacts_when_none_read(
        self, tmp_path: Path
    ) -> None:
        config = SEMANTIC_REGISTRY["no_forbidden_schema_authority"]
        prompt = _build_user_prompt(config, {}, {"sections_path": "missing/dir"})
        assert "No artifact files" in prompt


# ---------------------------------------------------------------------------
# _extract_json — standalone unit tests
# ---------------------------------------------------------------------------


class TestExtractJson:
    def test_bare_json_object_parsed(self) -> None:
        data = _extract_json('{"status": "pass"}')
        assert data == {"status": "pass"}

    def test_json_in_markdown_fence_extracted(self) -> None:
        text = '```json\n{"status": "fail"}\n```'
        data = _extract_json(text)
        assert data == {"status": "fail"}

    def test_json_surrounded_by_prose_extracted(self) -> None:
        text = 'Here is the result: {"status": "pass", "x": 1} End.'
        data = _extract_json(text)
        assert data is not None
        assert data["status"] == "pass"

    def test_non_json_returns_none(self) -> None:
        assert _extract_json("No JSON here.") is None

    def test_json_list_returns_none(self) -> None:
        assert _extract_json("[1, 2, 3]") is None

    def test_empty_string_returns_none(self) -> None:
        assert _extract_json("") is None


# ---------------------------------------------------------------------------
# DispatchSemanticPredicateRouting — public entry point
# ---------------------------------------------------------------------------


class TestDispatchSemanticPredicateRouting:
    def test_delegates_to_invoke_agent(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        """dispatch_semantic_predicate is a thin wrapper around invoke_agent."""
        _mock_transport_response(mock_transport, _valid_pass_result("p_x"))
        entry = _pred_entry("no_unsupported_tier5_claims", pred_id="p_x")
        result = dispatch_semantic_predicate(entry, "run-abc", tmp_path)
        assert result["predicate_id"] == "p_x"
        mock_transport.assert_called_once()

    def test_unknown_function_dispatch_error_propagated(
        self, tmp_path: Path
    ) -> None:
        entry = _pred_entry("completely_unknown_fn")
        result = dispatch_semantic_predicate(entry, "run-1", tmp_path)
        assert result.get("_dispatch_error") is True

    def test_transport_error_dispatch_error_propagated(
        self, mock_transport: MagicMock, tmp_path: Path
    ) -> None:
        mock_transport.side_effect = ClaudeTransportError("disk full")
        entry = _pred_entry("no_forbidden_schema_authority")
        result = dispatch_semantic_predicate(entry, "run-1", tmp_path)
        assert result.get("_dispatch_error") is True


# ---------------------------------------------------------------------------
# Module isolation
# ---------------------------------------------------------------------------


class TestModuleIsolation:
    def test_no_anthropic_import(self) -> None:
        """After transport migration, semantic_dispatch must not import anthropic."""
        import runner.semantic_dispatch as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import anthropic" not in source
