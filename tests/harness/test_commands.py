"""
Offline tests for the harness module commands (``harness.commands``).

The rubric grading runner has its own suite (``test_rubric_run.py``).  This file
covers the two runners that previously lived untested under ``scripts/``: the
paced/retrying backend wrapper from the E4 freeze runner, and the E1.5
calibration checkpoint loader.  No transport, no ``.env.harness``, no sleeping —
``time.sleep`` and ``time.monotonic`` are stubbed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.commands import _common
from harness.commands import faithfulness_calibration as fc
from harness.commands import freeze_grounding_baselines as fgb
from runner.transport.errors import ErrorCategory, OpenAICompatTransportError

COMMANDS = ("freeze_grounding_baselines", "faithfulness_calibration", "rubric_grading_run")


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, s: float) -> None:
        self.slept.append(s)
        self.now += s


@pytest.fixture
def clock(monkeypatch):
    c = _Clock()
    monkeypatch.setattr(fgb.time, "monotonic", c.monotonic)
    monkeypatch.setattr(fgb.time, "sleep", c.sleep)
    return c


class _Inner:
    """Fake ``OpenAICompatBackend``: scripted outcomes, reports ``last_usage``."""

    def __init__(self, outcomes, tokens=100):
        self._outcomes = list(outcomes)
        self.last_usage = {"total_tokens": tokens}
        self.calls = 0

    def __call__(self, messages):
        self.calls += 1
        out = self._outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def paced(inner, *, tpm=6000, rpm=0, max_retries=2, **kw) -> fgb.PacedRetryingBackend:
    return fgb.PacedRetryingBackend(
        inner, tpm_budget=tpm, rpm_budget=rpm, max_retries=max_retries, log=lambda *_: None, **kw
    )


def _rate_limited(body: str | None = None) -> OpenAICompatTransportError:
    return OpenAICompatTransportError(
        "429", status_code=429, category=ErrorCategory.RATE_LIMITED,
        retryable=True, response_body=body,
    )


class TestPacedRetryingBackend:
    def test_success_records_real_usage(self, clock):
        inner = _Inner([{"content": "ok"}], tokens=321)
        b = paced(inner, tpm=6000, rpm=0, max_retries=2)
        assert b(messages=[]) == {"content": "ok"}
        assert (b.calls, b.total_tokens, b.retries) == (1, 321, 0)

    def test_retryable_error_is_retried_with_backoff(self, clock):
        inner = _Inner([_rate_limited(), {"content": "ok"}])
        b = paced(inner, tpm=6000, rpm=0, max_retries=3, base_delay=8.0)
        assert b([]) == {"content": "ok"}
        assert inner.calls == 2 and b.retries == 1
        assert clock.slept == [8.0]

    def test_retry_after_hint_wins_over_backoff(self, clock):
        inner = _Inner([_rate_limited("Please try again in 12.5s"), {"content": "ok"}])
        b = paced(inner, tpm=6000, rpm=0, max_retries=3)
        b([])
        assert clock.slept == [13.0]

    def test_non_retryable_error_propagates_immediately(self, clock):
        err = OpenAICompatTransportError(
            "401", status_code=401, category=ErrorCategory.AUTH_FAILURE, retryable=False
        )
        inner = _Inner([err])
        b = paced(inner, tpm=6000, rpm=0, max_retries=3)
        with pytest.raises(OpenAICompatTransportError):
            b([])
        assert inner.calls == 1 and b.retries == 0 and clock.slept == []

    def test_retries_exhausted_reraises(self, clock):
        inner = _Inner([_rate_limited(), _rate_limited(), _rate_limited()])
        b = paced(inner, tpm=6000, rpm=0, max_retries=2)
        with pytest.raises(OpenAICompatTransportError):
            b([])
        assert inner.calls == 3 and b.retries == 2

    def test_rpm_floor_spaces_requests(self, clock):
        inner = _Inner([{"content": "a"}, {"content": "b"}])
        b = paced(inner, tpm=100000, rpm=30, max_retries=0)
        b([]); b([])
        assert clock.slept and clock.slept[0] == pytest.approx(2.0)

    def test_tpm_window_waits_for_headroom(self, clock):
        inner = _Inner([{"content": "a"}, {"content": "b"}], tokens=4000)
        b = paced(inner, tpm=6000, rpm=0, max_retries=0)
        b([])
        b([])  # 4000 in window + projected 4000 > 6000 -> wait out the window
        assert clock.slept and clock.slept[0] > 59.0


class TestCalibrationCheckpoint:
    def test_missing_file_is_fresh(self, tmp_path: Path):
        ck = fc._load_ckpt(tmp_path / "ckpt.json", "m@v1")
        assert ck == {"judge_pin": "m@v1", "pred": {}, "salvaged": [], "excluded": []}

    def test_same_pin_resumes_and_backfills_keys(self, tmp_path: Path):
        p = tmp_path / "ckpt.json"
        p.write_text(json.dumps({"judge_pin": "m@v1", "pred": {"p1": True}}), encoding="utf-8")
        ck = fc._load_ckpt(p, "m@v1")
        assert ck["pred"] == {"p1": True}
        assert ck["salvaged"] == [] and ck["excluded"] == []

    def test_different_pin_starts_fresh(self, tmp_path: Path):
        p = tmp_path / "ckpt.json"
        p.write_text(json.dumps({"judge_pin": "m@v0", "pred": {"p1": True}}), encoding="utf-8")
        assert fc._load_ckpt(p, "m@v1")["pred"] == {}

    def test_corrupt_file_is_fresh(self, tmp_path: Path):
        p = tmp_path / "ckpt.json"
        p.write_text("{not json", encoding="utf-8")
        assert fc._load_ckpt(p, "m@v1")["pred"] == {}


class TestImportIsSideEffectFree:
    def test_importing_commands_does_not_load_env_harness(self, monkeypatch):
        """``.env.harness`` (override=True) must load from ``main()`` only —
        an import must never flip the pipeline's transport preset."""
        import importlib
        import sys

        calls: list[str] = []
        try:
            import dotenv
        except Exception:
            pytest.skip("python-dotenv not installed")
        monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: calls.append(str(a[0]) if a else ""))
        for name in (*COMMANDS, "_common"):
            sys.modules.pop(f"harness.commands.{name}", None)
            importlib.import_module(f"harness.commands.{name}")
        assert calls == []

    def test_load_harness_env_is_what_main_calls(self, monkeypatch, tmp_path):
        seen: list = []
        import dotenv
        monkeypatch.setattr(dotenv, "load_dotenv", lambda p, **k: seen.append((Path(p).name, k)))
        monkeypatch.setattr(_common, "REPO_ROOT", tmp_path)
        _common.load_harness_env()
        assert seen == []  # no file -> no-op
        (tmp_path / ".env.harness").write_text("X=1", encoding="utf-8")
        _common.load_harness_env()
        assert seen == [(".env.harness", {"override": True})]
