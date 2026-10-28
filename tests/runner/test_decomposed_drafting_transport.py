"""R10 (F5): the Phase 8 decomposed drafter resolves its provider through the
transport layer, and under ``ORCHESTRATOR_PRODUCTION_MODE=true`` it never
reaches the Claude CLI transport.

The production drafter (``runner.decomposed_drafting._default_claude_drafter``)
used to import ``runner.claude_transport.invoke_claude_text`` directly, with no
provider resolution, so a production-mode run would have spawned the ``claude``
CLI.  These tests pin the environment with ``clear=True`` so that neither the
workstation ``.env`` nor a leaked ``.env.harness`` (F-R9-1) can reroute them,
replace ``boto3.client`` with a fake Converse client (the
``tests/harness/test_converse_judge.py`` pattern), and trip on any CLI call.

Decision record: ``aws-redeployment-r10-drafter-transport_2026-10-28``.
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Any, Iterator
from unittest import mock

import pytest

import runner.claude_transport as ct
import runner.transport.bedrock_converse as bc
from runner import persistence_policy
from runner.decomposed_drafting import (
    DecomposedDraftingError,
    _default_claude_drafter,
    draft_section_decomposed,
)
from tests.runner.test_excellence_decomposed_drafting import (
    _EXCELLENCE_SUBS,
    _seed_msca_excellence_profile,
)

RUN_ID = "run-r10-drafter-transport"
SENTINEL_MODEL = "eu.anthropic.r10-sentinel-model-v1:0"
SENTINEL_REGION = "eu-r10-sentinel-1"
CAPTURE_REL = ".claude/logs/decomposed_drafting"
PACK_REL = (
    "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/"
    "canonical_reference_pack.json"
)
OUTSIDE_REL = "docs/tier1_normative_framework/extracted/outside.json"

#: Production mode, the EU Converse preset, a sentinel Region and model.
PRODUCTION_CONVERSE_ENV: dict[str, str] = {
    "ORCHESTRATOR_PRODUCTION_MODE": "true",
    "ORCHESTRATOR_TRANSPORT_PRESET": "BEDROCK_CONVERSE_EU",
    "ORCHESTRATOR_TRANSPORT_MODEL": SENTINEL_MODEL,
    "AWS_REGION": SENTINEL_REGION,
}

_SUB = {
    "section_id": "1.1",
    "section_name": "Quality and pertinence of the objectives",
    "field_requirements": ["Describe the objectives."],
}


def _draft_json(sub_id: str = "1.1") -> str:
    return json.dumps(
        {
            "content": f"Grounded prose for {sub_id}.",
            "claim_statuses": [],
            "source_refs": [{"tier": 4, "source_path": PACK_REL}],
        }
    )


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def env() -> Iterator[Any]:
    """Pin ``os.environ`` (``clear=True``) and reset the diagnostic-level cache.

    Returns a setter: ``env(mapping)`` replaces the environment for the test.
    """
    persistence_policy.reset_diagnostic_level_cache()
    with mock.patch.dict(os.environ, {}, clear=True):

        def _set(values: dict[str, str]) -> None:
            os.environ.clear()
            os.environ.update(values)
            persistence_policy.reset_diagnostic_level_cache()

        yield _set
    persistence_policy.reset_diagnostic_level_cache()


@pytest.fixture
def cli_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Trip on any use of the Claude CLI transport: the drafter's entry point
    (``invoke_claude_text``) and the executable resolution behind it."""
    calls: list[dict[str, Any]] = []

    def _tripwire_invoke(**kwargs: Any) -> str:
        calls.append(kwargs)
        raise AssertionError("the Claude CLI transport was called")

    def _tripwire_resolve(*_a: Any, **_k: Any) -> Any:
        calls.append({"resolve_claude_cli": True})
        raise AssertionError("the claude executable was resolved")

    monkeypatch.setattr(ct, "invoke_claude_text", _tripwire_invoke)
    monkeypatch.setattr(ct, "resolve_claude_cli", _tripwire_resolve)
    return calls


class FakeConverseClient:
    """Stands in for ``boto3.client('bedrock-runtime')``; answers from a script.

    Each scripted reply is either a string (a final text turn) or a dict
    ``{"tool": name, "input": {...}}`` (a toolUse turn).  The last reply
    repeats once the script is exhausted.
    """

    def __init__(self, script: list[Any]) -> None:
        self.script = list(script)
        self.requests: list[dict[str, Any]] = []
        self.client_kwargs: dict[str, Any] = {}

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.requests.append(kwargs)
        idx = min(len(self.requests) - 1, len(self.script) - 1)
        reply = self.script[idx]
        if isinstance(reply, BaseException):
            raise reply
        if isinstance(reply, dict):
            block = {
                "toolUse": {
                    "toolUseId": f"tu-{len(self.requests)}",
                    "name": reply["tool"],
                    "input": reply["input"],
                }
            }
        else:
            block = {"text": reply}
        return {
            "output": {"message": {"role": "assistant", "content": [block]}},
            "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
        }


@pytest.fixture
def converse(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Install a fake Converse client; returns a setter for its script."""
    holder: dict[str, FakeConverseClient] = {}

    def _install(script: list[Any]) -> FakeConverseClient:
        fake = FakeConverseClient(script)

        def _factory(service: str, **kwargs: Any) -> FakeConverseClient:
            assert service == "bedrock-runtime"
            fake.client_kwargs = kwargs
            return fake

        monkeypatch.setattr(bc.boto3, "client", _factory)
        holder["fake"] = fake
        return fake

    return _install


def _seed_inputs(repo_root: Path) -> None:
    pack = repo_root / PACK_REL
    pack.parent.mkdir(parents=True, exist_ok=True)
    pack.write_text('{"partners": []}', encoding="utf-8")
    outside = repo_root / OUTSIDE_REL
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text('{"not": "a grounding input"}', encoding="utf-8")


def _tool_result_texts(request: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for message in request["messages"]:
        for block in message["content"]:
            if "toolResult" in block:
                texts.extend(c.get("text", "") for c in block["toolResult"]["content"])
    return texts


def _capture_files(repo_root: Path, slug: str = "excellence") -> dict[str, str]:
    cap = repo_root / CAPTURE_REL / RUN_ID / slug
    if not cap.is_dir():
        return {}
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(cap.iterdir())}


# --------------------------------------------------------------------------- #
# Criterion 1: under production mode the drafter never calls the CLI transport
# --------------------------------------------------------------------------- #


class TestProductionModeNeverReachesTheCli:
    def test_production_converse_drafts_without_the_cli(
        self, tmp_path: Path, env: Any, cli_calls: list, converse: Any
    ) -> None:
        env(PRODUCTION_CONVERSE_ENV)
        _seed_inputs(tmp_path)
        fake = converse([{"tool": "Read", "input": {"file_path": PACK_REL}}, _draft_json()])

        drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
        out = drafter(_SUB, "Excellence", [])

        assert out["content"] == "Grounded prose for 1.1."
        assert cli_calls == []
        assert len(fake.requests) == 2
        first = fake.requests[0]
        assert first["modelId"] == SENTINEL_MODEL
        assert fake.client_kwargs["region_name"] == SENTINEL_REGION
        assert first["inferenceConfig"]["maxTokens"] == 32000
        assert first["inferenceConfig"]["temperature"] == 0.0
        tool_names = {t["toolSpec"]["name"] for t in first["toolConfig"]["tools"]}
        assert tool_names == {"Read", "Glob"}
        # The grounding input was served from disk by the Python tool executor.
        assert any('"partners"' in t for t in _tool_result_texts(fake.requests[1]))

    @pytest.mark.parametrize(
        "cli_env",
        [
            {"ORCHESTRATOR_TRANSPORT_BACKEND": "claude_cli"},
            {"ORCHESTRATOR_TRANSPORT_PRESET": "CLAUDE_REFERENCE"},
            {},  # no backend named: the transport's default is claude_cli
        ],
        ids=["backend-claude_cli", "preset-CLAUDE_REFERENCE", "backend-default"],
    )
    def test_production_cli_configuration_is_refused_before_any_call(
        self, tmp_path: Path, env: Any, cli_calls: list, cli_env: dict[str, str]
    ) -> None:
        env({"ORCHESTRATOR_PRODUCTION_MODE": "true", "AWS_REGION": SENTINEL_REGION, **cli_env})

        with pytest.raises(ValueError, match="ORCHESTRATOR_PRODUCTION_MODE=true"):
            drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
            drafter(_SUB, "Excellence", [])
        assert cli_calls == []

    def test_draft_section_decomposed_in_production_mode_uses_converse(
        self, tmp_path: Path, env: Any, cli_calls: list, converse: Any
    ) -> None:
        env(PRODUCTION_CONVERSE_ENV)
        _seed_msca_excellence_profile(tmp_path)
        fake = converse([_draft_json()])

        paths = draft_section_decomposed(RUN_ID, tmp_path, "excellence", extra_fields={})

        assert cli_calls == []
        assert len(fake.requests) == len(_EXCELLENCE_SUBS)
        assert len(paths) == 1 + len(_EXCELLENCE_SUBS)
        assert all(p.is_file() for p in paths)

    def test_production_refusal_leaves_prior_drafts_intact(
        self, tmp_path: Path, env: Any, cli_calls: list
    ) -> None:
        env({"ORCHESTRATOR_PRODUCTION_MODE": "true", "ORCHESTRATOR_TRANSPORT_BACKEND": "claude_cli"})
        _seed_msca_excellence_profile(tmp_path)
        from runner.section_assembler import SECTION_DRAFTS_ROOT_REL

        drafts_dir = tmp_path / SECTION_DRAFTS_ROOT_REL / "excellence"
        drafts_dir.mkdir(parents=True)
        prior = drafts_dir / "1.1.draft.json"
        prior.write_text("{}", encoding="utf-8")

        with pytest.raises(ValueError, match="ORCHESTRATOR_PRODUCTION_MODE=true"):
            draft_section_decomposed(RUN_ID, tmp_path, "excellence", extra_fields={})
        assert prior.is_file()
        assert cli_calls == []


class TestCliTransportRefusesUnderProductionMode:
    """Defence in depth (R10 point 6): the CLI transport itself fails closed."""

    def test_invoke_claude_text_refuses_before_resolving_the_cli(
        self, env: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env({"ORCHESTRATOR_PRODUCTION_MODE": "true"})
        resolved: list[bool] = []

        def _tripwire_resolve(*_a: Any, **_k: Any) -> Any:
            resolved.append(True)
            raise AssertionError("the claude executable was resolved")

        monkeypatch.setattr(ct, "resolve_claude_cli", _tripwire_resolve)
        monkeypatch.setattr(
            ct.subprocess, "Popen",
            mock.Mock(side_effect=AssertionError("a subprocess was spawned")),
        )

        with pytest.raises(ct.ClaudeTransportError) as info:
            ct.invoke_claude_text(
                system_prompt="s", user_prompt="u", model="m", max_tokens=1
            )
        assert "ORCHESTRATOR_PRODUCTION_MODE=true" in str(info.value)
        error_type = getattr(ct, "ClaudeCLIProductionModeError", None)
        assert error_type is not None and isinstance(info.value, error_type)
        assert isinstance(info.value, ct.ClaudeCLIUnavailableError)
        assert resolved == []


# --------------------------------------------------------------------------- #
# The tool loop path: TAPM boundary, failure modes
# --------------------------------------------------------------------------- #


class TestConverseToolLoop:
    def test_read_outside_the_grounding_inputs_is_refused(
        self, tmp_path: Path, env: Any, cli_calls: list, converse: Any
    ) -> None:
        env(PRODUCTION_CONVERSE_ENV)
        _seed_inputs(tmp_path)
        fake = converse([{"tool": "Read", "input": {"file_path": OUTSIDE_REL}}, _draft_json()])

        drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
        drafter(_SUB, "Excellence", [])

        results = _tool_result_texts(fake.requests[1])
        assert results and all("not in the declared inputs" in r for r in results)
        assert not any("a grounding input" in r for r in results)

    def test_exhausted_tool_loop_fails_closed(
        self, tmp_path: Path, env: Any, cli_calls: list, converse: Any
    ) -> None:
        env(PRODUCTION_CONVERSE_ENV)
        _seed_inputs(tmp_path)
        # A model that never stops calling tools: the loop hits max_rounds.
        converse([{"tool": "Glob", "input": {"pattern": "docs/**/*.json"}}])

        drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
        with pytest.raises(DecomposedDraftingError, match="exhausted|empty"):
            drafter(_SUB, "Excellence", [])

    def test_empty_final_reply_fails_closed(
        self, tmp_path: Path, env: Any, cli_calls: list, converse: Any
    ) -> None:
        env(PRODUCTION_CONVERSE_ENV)
        converse([""])
        drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
        with pytest.raises(DecomposedDraftingError, match="empty"):
            drafter(_SUB, "Excellence", [])

    def test_missing_model_is_refused(
        self, tmp_path: Path, env: Any, cli_calls: list, converse: Any
    ) -> None:
        env({k: v for k, v in PRODUCTION_CONVERSE_ENV.items() if k != "ORCHESTRATOR_TRANSPORT_MODEL"})
        fake = converse([_draft_json()])
        with pytest.raises(ValueError, match="model is required"):
            drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
            drafter(_SUB, "Excellence", [])
        assert fake.requests == []

    def test_backend_without_tool_calling_is_refused(
        self, tmp_path: Path, env: Any, cli_calls: list, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import runner.transport.config as tc

        env({"ORCHESTRATOR_TRANSPORT_BACKEND": "ollama", "ORCHESTRATOR_TRANSPORT_MODEL": "m"})
        real = tc.resolve_provider_config

        def _no_tools() -> Any:
            cfg = real()
            return dataclasses.replace(
                cfg, capabilities=dataclasses.replace(cfg.capabilities, tool_calling=False)
            )

        monkeypatch.setattr(tc, "resolve_provider_config", _no_tools)
        with pytest.raises(DecomposedDraftingError, match="tool calling"):
            drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
            drafter(_SUB, "Excellence", [])
        assert cli_calls == []

    def test_transport_error_is_reraised_unchanged(
        self, tmp_path: Path, env: Any, cli_calls: list, converse: Any
    ) -> None:
        from botocore.exceptions import ClientError

        from runner.transport.errors import OpenAICompatTransportError

        env(PRODUCTION_CONVERSE_ENV)
        throttled = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "slow down"}}, "Converse"
        )
        fake = converse([throttled])
        drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
        with pytest.raises(OpenAICompatTransportError, match="rate limited"):
            drafter(_SUB, "Excellence", [])
        assert len(fake.requests) == 1  # §17.5.4: no retry


# --------------------------------------------------------------------------- #
# DC-35: the drafter honours the diagnostic level
# --------------------------------------------------------------------------- #


class TestDiagnosticLevel:
    def test_metadata_level_writes_no_response_content(
        self, tmp_path: Path, env: Any, cli_calls: list, converse: Any
    ) -> None:
        env(PRODUCTION_CONVERSE_ENV)  # production mode => metadata
        converse([_draft_json()])
        drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
        drafter(_SUB, "Excellence", [])

        files = _capture_files(tmp_path)
        assert set(files) == {"1.1.response_meta.json"}
        meta = json.loads(files["1.1.response_meta.json"])
        assert meta["sub_section_id"] == "1.1"
        assert meta["backend"] == "bedrock_converse"
        assert meta["response_chars"] == len(_draft_json())
        assert "Grounded prose" not in files["1.1.response_meta.json"]

    def test_metadata_level_parse_failure_carries_no_excerpt(
        self, tmp_path: Path, env: Any, cli_calls: list, converse: Any
    ) -> None:
        env(PRODUCTION_CONVERSE_ENV)
        converse(["SECRET-RESPONSE-PROSE that is not JSON at all"])
        drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
        with pytest.raises(DecomposedDraftingError) as info:
            drafter(_SUB, "Excellence", [])
        assert "SECRET-RESPONSE-PROSE" not in str(info.value)
        assert "response length" in str(info.value)
        assert all("SECRET-RESPONSE-PROSE" not in t for t in _capture_files(tmp_path).values())

    def test_metadata_level_transport_failure_writes_metadata_only(
        self, tmp_path: Path, env: Any, cli_calls: list, converse: Any
    ) -> None:
        from botocore.exceptions import ClientError

        env(PRODUCTION_CONVERSE_ENV)
        converse([ClientError({"Error": {"Code": "ThrottlingException", "Message": "slow"}}, "Converse")])
        drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
        with pytest.raises(Exception):
            drafter(_SUB, "Excellence", [])

        files = _capture_files(tmp_path)
        assert set(files) == {"1.1.response_meta.json"}
        meta = json.loads(files["1.1.response_meta.json"])
        assert meta["exception_class"] == "OpenAICompatTransportError"
        assert len(meta["error"]) <= persistence_policy.PRODUCTION_ERROR_MESSAGE_MAX_LENGTH + len(" [TRUNCATED]")

    def test_full_level_keeps_the_raw_response(
        self, tmp_path: Path, env: Any, cli_calls: list, converse: Any
    ) -> None:
        env({
            "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock_converse",
            "ORCHESTRATOR_TRANSPORT_MODEL": SENTINEL_MODEL,
            "AWS_REGION": SENTINEL_REGION,
        })  # non-production, level unset => full
        converse([_draft_json()])
        drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
        drafter(_SUB, "Excellence", [])
        files = _capture_files(tmp_path)
        assert files.get("1.1.response.txt") == _draft_json()


# --------------------------------------------------------------------------- #
# Criterion 2: the workstation's non-production path stays on the CLI
# --------------------------------------------------------------------------- #


class TestNonProductionCliPathUnchanged:
    @pytest.mark.parametrize(
        "cli_env",
        [{"ORCHESTRATOR_TRANSPORT_PRESET": "CLAUDE_REFERENCE"}, {}],
        ids=["preset-CLAUDE_REFERENCE", "backend-default"],
    )
    def test_cli_path_keeps_the_drafter_constants(
        self, tmp_path: Path, env: Any, monkeypatch: pytest.MonkeyPatch,
        cli_env: dict[str, str],
    ) -> None:
        env(cli_env)
        captured: dict[str, Any] = {}

        def _fake_invoke(**kwargs: Any) -> str:
            captured.update(kwargs)
            return _draft_json()

        monkeypatch.setattr(ct, "invoke_claude_text", _fake_invoke)
        drafter = _default_claude_drafter(tmp_path, run_id=RUN_ID, slug="excellence")
        out = drafter(_SUB, "Excellence", [])

        assert out["content"] == "Grounded prose for 1.1."
        assert captured["model"] == "claude-opus-4-8"
        assert captured["tools"] == ["Read", "Glob"]
        assert captured["timeout_seconds"] == 1800
        assert _capture_files(tmp_path).get("1.1.response.txt") == _draft_json()
