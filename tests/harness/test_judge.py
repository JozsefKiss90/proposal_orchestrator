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
        assert "claude-opus-4-8" in drafter_models()


class TestDrafterModelsOnTheHost:
    """AN1c on the private host (R9e point 8; OD7-assessor).

    Under production mode the pipeline drafts with ``ORCHESTRATOR_TRANSPORT_MODEL``
    (the runtime secret's), so the guard must count it; outside production mode
    it must not, because the workstation's ``.env.harness`` puts the judge's own
    model there. Decision record ``aws-redeployment-r9e-eu-region_2026-10-27``.
    """

    HOST_DRAFTER = "zz.sentinel.drafter-model-v1"

    @pytest.fixture
    def env(self, monkeypatch):
        for name in ("ORCHESTRATOR_PRODUCTION_MODE", "ORCHESTRATOR_TRANSPORT_MODEL"):
            monkeypatch.delenv(name, raising=False)
        return monkeypatch

    def test_production_mode_counts_the_transport_model(self, env):
        env.setenv("ORCHESTRATOR_PRODUCTION_MODE", "true")
        env.setenv("ORCHESTRATOR_TRANSPORT_MODEL", self.HOST_DRAFTER)
        assert self.HOST_DRAFTER in drafter_models()
        assert "claude-opus-4-8" in drafter_models()

    def test_production_mode_is_case_insensitive_like_the_transport(self, env):
        from runner.transport.config import is_production_mode

        for value in ("TRUE", "True", "true", "yes", "1", ""):
            env.setenv("ORCHESTRATOR_PRODUCTION_MODE", value)
            env.setenv("ORCHESTRATOR_TRANSPORT_MODEL", self.HOST_DRAFTER)
            assert (self.HOST_DRAFTER in drafter_models()) is is_production_mode(), value

    def test_a_judge_on_the_host_drafters_model_is_refused_in_any_id_form(self, env):
        env.setenv("ORCHESTRATOR_PRODUCTION_MODE", "true")
        env.setenv("ORCHESTRATOR_TRANSPORT_MODEL", "eu.zzvendor.sentinel-model-9-v1")
        for form in ("eu.zzvendor.sentinel-model-9-v1", "zzvendor.sentinel-model-9-v1",
                     "arn:aws:bedrock:zz-sentinel-1::foundation-model/zzvendor.sentinel-model-9-v1"):
            with pytest.raises(JudgeIndependenceError, match="independence"):
                _cfg(model=form)

    def test_outside_production_the_transport_model_is_not_a_drafter(self, env):
        # The workstation: .env.harness names the judge's model here.
        env.setenv("ORCHESTRATOR_TRANSPORT_MODEL", NON_DRAFTER)
        assert NON_DRAFTER not in drafter_models()
        assert _cfg(model=NON_DRAFTER).model == NON_DRAFTER

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_production_mode_with_no_transport_model_keeps_the_constants(self, env, blank):
        env.setenv("ORCHESTRATOR_PRODUCTION_MODE", "true")
        env.setenv("ORCHESTRATOR_TRANSPORT_MODEL", blank)
        from runner.semantic_dispatch import AGENT_MODEL
        from runner.skill_runtime import SKILL_MODEL

        assert drafter_models() == frozenset({SKILL_MODEL, AGENT_MODEL})


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
        # Malformed on every draw: the redraw budget is spent, then it raises.
        judge = Judge(_cfg(), backend=_Backend([content] * 3))
        with pytest.raises(JudgeResponseError):
            judge.evaluate("s", "u", metric="m", property_key="C1")

    def test_empty_content_raises(self):
        judge = Judge(_cfg(), backend=_Backend([None]))
        with pytest.raises(JudgeResponseError, match="empty content"):
            judge.evaluate("s", "u", metric="m", property_key="C1")


# --------------------------------------------------------------------------- #
# ask(): the one call path and the redraw rule (ticket 01)
# --------------------------------------------------------------------------- #

PASS = '{"passed": true, "score": 0.9, "rationale": "ok"}'
BAD = '{"rationale": "no verdict"}'


class TestAsk:
    def test_a_parser_raising_anything_else_propagates_with_no_redraw(self, tmp_path):
        """Ticket 01, test 3: only JudgeResponseError means malformed."""
        from harness.response_cache import CacheBinding, ResponseCache

        backend = _Backend([PASS, PASS, PASS])
        cache = ResponseCache(
            tmp_path / "ck.jsonl",
            CacheBinding(
                candidate_hash="sha256:" + "a" * 64,
                profile_version="sha256:" + "b" * 64,
                assessor_pin=f"{NON_DRAFTER}@2026-07-20",
                preflight_pack_set_hash="sha256:" + "c" * 64,
                include_claims=False,
                n=3,
                criterion_samples=5,
                temperature=0.0,
                max_tokens=2048,
            ),
        )
        log = ProvenanceLog(tmp_path / "p.jsonl")
        judge = Judge(_cfg(), backend=backend, provenance_log=log, response_cache=cache)

        def parser(raw: str):
            raise KeyError("a defect in the parser, not a malformed draw")

        with pytest.raises(KeyError, match="defect"):
            judge.ask("s", "u", parser, metric="m", property_key="C1")
        assert len(backend.calls) == 1
        assert cache.discarded == 0
        assert len(log) == 0

    def test_a_majority_vote_with_one_redraw_still_has_n_verdicts(self, tmp_path):
        """Ticket 01, test 4: the redraw replaces the malformed sample."""
        backend = _Backend([PASS, BAD, PASS, PASS])
        log = ProvenanceLog(tmp_path / "p.jsonl")
        judge = Judge(_cfg(), backend=backend, provenance_log=log)
        res = judge.evaluate_majority("s", "u", metric="m", property_key="C1", n=3)
        assert len(res.verdicts) == 3
        assert res.majority.n == 3
        assert [p.sample_index for p in res.provenance] == [0, 1, 2]
        assert len(log) == 3
        assert len(backend.calls) == 4
        (draw,) = res.discarded_draws
        assert draw.sample_index == 1 and draw.attempt == 0
        assert "neither 'passed' nor 'score'" in draw.reason
        assert "replayed" not in draw.to_dict()

    def test_a_replayed_malformed_draw_uses_budget_and_is_marked_replayed(self, tmp_path):
        """Ticket 01, test 5."""
        from harness.provenance import prompt_hash
        from harness.response_cache import CacheBinding, ResponseCache

        binding = CacheBinding(
            candidate_hash="sha256:" + "a" * 64,
            profile_version="sha256:" + "b" * 64,
            assessor_pin=f"{NON_DRAFTER}@2026-07-20",
            preflight_pack_set_hash="sha256:" + "c" * 64,
            include_claims=False,
            n=3,
            criterion_samples=5,
            temperature=0.0,
            max_tokens=2048,
        )
        path = tmp_path / "ck.jsonl"
        # A checkpoint holding three responses the parser now rejects (as when
        # a parser grew stricter after the run that drew them).
        first = ResponseCache(path, binding)
        for _ in range(3):
            first.record(prompt_hash("s", "u"), BAD)

        backend = _Backend([PASS])
        judge = Judge(_cfg(), backend=backend, response_cache=ResponseCache(path, binding, resume=True))
        with pytest.raises(JudgeResponseError, match=r"3 draw\(s\)"):
            judge.evaluate("s", "u", metric="m", property_key="C1")
        assert backend.calls == []  # the budget was spent on replays alone

        second = tmp_path / "ck2.jsonl"
        cache = ResponseCache(second, binding)
        cache.record(prompt_hash("s", "u"), BAD)
        judge = Judge(_cfg(), backend=_Backend([PASS]), response_cache=ResponseCache(second, binding, resume=True))
        res = judge.evaluate("s", "u", metric="m", property_key="C1")
        assert res.verdict.passed is True
        (draw,) = res.discarded_draws
        assert draw.replayed is True
        assert draw.to_dict()["replayed"] is True
        assert res.provenance.replayed is False  # the draw that parsed was live

    def test_budget_exhaustion_fails_closed_with_the_parsers_message_and_the_count(self):
        backend = _Backend([BAD] * 5)
        judge = Judge(_cfg(), backend=backend, max_redraws=1)
        with pytest.raises(JudgeResponseError) as exc:
            judge.evaluate("s", "u", metric="m", property_key="C1", sample_index=2)
        message = str(exc.value)
        assert "neither 'passed' nor 'score'" in message
        assert "m/C1 sample 2: 2 draw(s)" in message
        assert "nothing was repaired" in message
        assert len(backend.calls) == 2

    def test_the_value_reports_its_own_provenance(self, tmp_path):
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class Sample:
            raw_score: float

            @property
            def score(self):
                return self.raw_score / 5

            passed = None
            rationale = "a reason of its own"

        log = ProvenanceLog(tmp_path / "p.jsonl")
        judge = Judge(_cfg(), backend=_Backend(["4"]), provenance_log=log, clock=lambda: "T")
        answer = judge.ask("s", "u", lambda raw: Sample(float(raw)), metric="m", property_key="k", sample_index=0)
        assert answer.value.raw_score == 4.0
        (record,) = log.records()
        assert record["score"] == 0.8 and record["passed"] is None
        assert record["rationale"] == "a reason of its own"
        assert record["timestamp"] == "T" and record["sample_index"] == 0
        assert answer.discarded_draws == ()

    def test_no_harness_module_outside_the_judge_draws_raw(self):
        """The prompt-and-parser call is the only way a draw goes out."""
        import re
        from pathlib import Path

        root = Path(__file__).resolve().parents[2] / "harness"
        offenders = [
            p.relative_to(root).as_posix()
            for p in root.rglob("*.py")
            if p.name != "judge.py"
            and re.search(r"\.(_send|raw_invoke)\(", p.read_text(encoding="utf-8"))
        ]
        assert offenders == []

    def test_a_negative_budget_is_refused(self):
        with pytest.raises(JudgeConfigError, match="max_redraws"):
            Judge(_cfg(), backend=_Backend([]), max_redraws=-1)


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
# Backend independence (the judge factory's openai-compatible route)
# --------------------------------------------------------------------------- #


class TestFactoryBackendIndependence:
    def test_claude_cli_backend_rejected(self, monkeypatch):
        from harness.judge_factory import ROUTE_OPENAI_COMPATIBLE, build_judge
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
        with pytest.raises(JudgeIndependenceError, match="OpenAI-compatible"):
            build_judge(ROUTE_OPENAI_COMPATIBLE, _cfg())

    def test_pins_judge_model_on_build(self, monkeypatch):
        from harness.judge_factory import ROUTE_OPENAI_COMPATIBLE, build_judge
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

        judge, _wrapper = build_judge(ROUTE_OPENAI_COMPATIBLE, _cfg(model=NON_DRAFTER))
        res = judge.evaluate("s", "u", metric="m", property_key="C1")
        assert res.verdict.passed is True
        # the pinned judge model overrides the env default; temp 0 passed through
        assert captured["model"] == NON_DRAFTER
        assert captured["temperature"] == 0.0
