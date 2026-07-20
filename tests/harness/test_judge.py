"""
Tests for harness/judge.py — pinned non-drafter judge over the OpenAI-compatible
transport, with an injected fake backend (no network, no httpx).

Covers:
  - JudgeConfig: pin (model/version), temp-0, non-drafter independence guard
  - resolve_judge_config from env
  - evaluate(): parses {passed, score, rationale}, returns verdict + provenance,
    logs to an attached ProvenanceLog
  - no silent repair: empty / non-JSON / no-verdict / bad-type / out-of-range raise
  - evaluate_majority(): n≥3, combines via majority_vote, captures all provenance
  - default backend rejects claude_cli (independence); pins the judge model
"""

from __future__ import annotations

from typing import Any

import pytest

from harness.judge import (
    Judge,
    JudgeConfig,
    JudgeConfigError,
    JudgeIndependenceError,
    JudgeResponseError,
    drafter_models,
    resolve_judge_config,
)
from harness.provenance import ProvenanceLog


# --------------------------------------------------------------------------- #
# Fake backend
# --------------------------------------------------------------------------- #


class _Backend:
    """Returns programmed content strings in order (ToolLoopBackend shape)."""

    def __init__(self, contents: list[str | None]) -> None:
        self._contents = list(contents)
        self.calls: list[list[dict[str, Any]]] = []

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self.calls.append(messages)
        content = self._contents.pop(0) if self._contents else '{"passed": true, "rationale": "ok"}'
        return {"content": content, "tool_calls": None}


NON_DRAFTER = "acme-judge-1"


def _cfg(model: str = NON_DRAFTER, version: str = "2026-07-20", **kw) -> JudgeConfig:
    return JudgeConfig(model=model, version=version, **kw)


# --------------------------------------------------------------------------- #
# JudgeConfig
# --------------------------------------------------------------------------- #


class TestJudgeConfig:
    def test_valid(self):
        c = _cfg()
        assert c.temperature == 0.0
        assert c.model == NON_DRAFTER

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_model(self, blank):
        with pytest.raises(JudgeConfigError, match="model"):
            _cfg(model=blank)

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_version(self, blank):
        with pytest.raises(JudgeConfigError, match="version"):
            _cfg(version=blank)

    @pytest.mark.parametrize("temp", [0.1, 0.7, 1.0])
    def test_nonzero_temperature_rejected(self, temp):
        with pytest.raises(JudgeConfigError, match="temperature"):
            _cfg(temperature=temp)

    def test_drafter_model_rejected(self):
        drafter = next(iter(drafter_models()))
        with pytest.raises(JudgeIndependenceError, match="independence"):
            _cfg(model=drafter)

    def test_drafter_models_includes_pipeline_models(self):
        assert "claude-sonnet-4-6" in drafter_models()


class TestResolveJudgeConfig:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("HARNESS_JUDGE_MODEL", NON_DRAFTER)
        monkeypatch.setenv("HARNESS_JUDGE_VERSION", "v9")
        monkeypatch.delenv("HARNESS_JUDGE_MAX_TOKENS", raising=False)
        c = resolve_judge_config()
        assert c.model == NON_DRAFTER
        assert c.version == "v9"

    def test_missing_env_raises(self, monkeypatch):
        monkeypatch.delenv("HARNESS_JUDGE_MODEL", raising=False)
        monkeypatch.delenv("HARNESS_JUDGE_VERSION", raising=False)
        with pytest.raises(JudgeConfigError, match="HARNESS_JUDGE_MODEL"):
            resolve_judge_config()


# --------------------------------------------------------------------------- #
# evaluate()
# --------------------------------------------------------------------------- #


class TestEvaluate:
    def test_parses_verdict_and_logs_provenance(self, tmp_path):
        backend = _Backend(['{"passed": false, "score": 0.2, "rationale": "unsupported"}'])
        log = ProvenanceLog(tmp_path / "prov.jsonl")
        judge = Judge(_cfg(), backend=backend, provenance_log=log, clock=lambda: "2026-07-20T00:00:00+00:00")

        res = judge.evaluate("SYS", "USR", metric="faithfulness", property_key="C07")

        assert res.verdict.passed is False
        assert res.verdict.score == 0.2
        assert res.verdict.rationale == "unsupported"
        assert res.verdict.evidence_type == "Inferred"
        # provenance carries the pinned identity + prompt hash + score
        assert res.provenance.judge_model == NON_DRAFTER
        assert res.provenance.judge_version == "2026-07-20"
        assert res.provenance.prompt_hash.startswith("sha256:")
        assert res.provenance.timestamp == "2026-07-20T00:00:00+00:00"
        # logged
        assert len(log) == 1
        assert log.records()[0]["score"] == 0.2

    def test_passed_only_verdict(self):
        judge = Judge(_cfg(), backend=_Backend(['{"passed": true, "rationale": "grounded"}']))
        res = judge.evaluate("s", "u", metric="m", property_key="C1")
        assert res.verdict.passed is True
        assert res.verdict.score is None

    def test_score_only_verdict(self):
        judge = Judge(_cfg(), backend=_Backend(['{"score": 0.9, "rationale": "mostly on-topic"}']))
        res = judge.evaluate("s", "u", metric="relevancy", property_key="C1")
        assert res.verdict.passed is None
        assert res.verdict.score == 0.9

    def test_fenced_json_ok(self):
        judge = Judge(_cfg(), backend=_Backend(['```json\n{"passed": true, "rationale": "x"}\n```']))
        res = judge.evaluate("s", "u", metric="m", property_key="C1")
        assert res.verdict.passed is True

    def test_no_provenance_log_ok(self):
        judge = Judge(_cfg(), backend=_Backend(['{"passed": true, "rationale": "x"}']))
        res = judge.evaluate("s", "u", metric="m", property_key="C1")
        assert res.provenance.judge_model == NON_DRAFTER  # still produced


class TestNoSilentRepair:
    @pytest.mark.parametrize(
        "content",
        [
            "",  # empty
            "not json at all",  # unparseable
            "{}",  # neither passed nor score
            '{"rationale": "only a reason"}',  # no verdict
            '{"passed": "yes", "rationale": "x"}',  # wrong type
            '{"score": "high", "rationale": "x"}',  # wrong type
            '{"score": 1.5, "rationale": "x"}',  # out of range
        ],
    )
    def test_malformed_raises(self, content):
        judge = Judge(_cfg(), backend=_Backend([content]))
        with pytest.raises(JudgeResponseError):
            judge.evaluate("s", "u", metric="m", property_key="C1")

    def test_empty_content_raises(self):
        judge = Judge(_cfg(), backend=_Backend([None]))
        with pytest.raises(JudgeResponseError, match="empty content"):
            judge.evaluate("s", "u", metric="m", property_key="C1")


# --------------------------------------------------------------------------- #
# evaluate_majority()
# --------------------------------------------------------------------------- #


class TestEvaluateMajority:
    def test_three_samples_combined(self, tmp_path):
        backend = _Backend(
            [
                '{"passed": true, "score": 0.9, "rationale": "a"}',
                '{"passed": true, "score": 0.8, "rationale": "b"}',
                '{"passed": false, "score": 0.4, "rationale": "c"}',
            ]
        )
        log = ProvenanceLog(tmp_path / "p.jsonl")
        judge = Judge(_cfg(), backend=backend, provenance_log=log)
        res = judge.evaluate_majority("s", "u", metric="faithfulness", property_key="C1", n=3)

        assert res.majority.passed is True  # 2 of 3
        assert res.majority.n == 3
        assert res.majority.evidence_type == "Inferred"
        assert len(res.verdicts) == 3
        # every sample's provenance captured AND logged, with sample_index set
        assert len(res.provenance) == 3
        assert [p.sample_index for p in res.provenance] == [0, 1, 2]
        assert len(log) == 3

    def test_n_below_three_rejected(self):
        judge = Judge(_cfg(), backend=_Backend([]))
        with pytest.raises(ValueError, match="n≥3"):
            judge.evaluate_majority("s", "u", metric="m", property_key="C1", n=2)


# --------------------------------------------------------------------------- #
# Default backend independence
# --------------------------------------------------------------------------- #


class TestDefaultBackendIndependence:
    def test_claude_cli_backend_rejected(self, monkeypatch):
        from runner.transport.capabilities import CAPABILITIES_REGISTRY
        from runner.transport.config import ProviderConfig

        claude_cfg = ProviderConfig(
            backend_name="claude_cli",
            base_url=None,
            api_key_set=False,
            model=None,
            capabilities=CAPABILITIES_REGISTRY["claude_cli"],
        )
        monkeypatch.setattr(
            "runner.transport.config.resolve_provider_config", lambda: claude_cfg
        )
        judge = Judge(_cfg())  # no injected backend -> tries to build default
        with pytest.raises(JudgeIndependenceError, match="OpenAI-compatible"):
            judge.raw_invoke("s", "u")

    def test_pins_judge_model_on_build(self, monkeypatch):
        from runner.transport.capabilities import CAPABILITIES_REGISTRY
        from runner.transport.config import ProviderConfig

        oai_cfg = ProviderConfig(
            backend_name="openai_compatible",
            base_url="https://example.test/v1",
            api_key_set=True,
            model="env-default-model",
            capabilities=CAPABILITIES_REGISTRY["openai_compatible"],
        )
        monkeypatch.setattr(
            "runner.transport.config.resolve_provider_config", lambda: oai_cfg
        )
        captured: dict[str, Any] = {}

        def _fake_build(provider, **kw):
            captured["model"] = provider.model
            captured["temperature"] = kw.get("temperature")
            return _Backend(['{"passed": true, "rationale": "ok"}'])

        monkeypatch.setattr("runner.transport.config.build_openai_backend", _fake_build)

        judge = Judge(_cfg(model=NON_DRAFTER))
        res = judge.evaluate("s", "u", metric="m", property_key="C1")
        assert res.verdict.passed is True
        # the pinned judge model overrides the env default; temp 0 passed through
        assert captured["model"] == NON_DRAFTER
        assert captured["temperature"] == 0.0
