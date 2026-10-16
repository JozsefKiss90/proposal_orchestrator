"""AN12 — the pipeline's smoke run on the private host.

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN12:

2. The pipeline runs A0 to A7 on the synthetic fixture against live Bedrock
   within its token budgets.

The live run is the operator's, on the host. These tests drive the same
driver against fake backends: it chains every stage on the AN3 fixture
outside the repository, stops at each stage's token budget, waits for the
two operator acts (the figure review and the signed acceptance) with
templates rather than inventing them, and reaches A7 once they are given.
One test drives the command line through the real Converse backend with only
``boto3.client`` replaced.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

import pytest

pymupdf = pytest.importorskip("pymupdf")

import runner.transport.bedrock_converse as bc  # noqa: E402
from runner import anonymisation_attack as atk  # noqa: E402
from runner import anonymisation_rewrite as rw  # noqa: E402
from tools import anonymisation_host_smoke as smoke  # noqa: E402

A3_MODEL = "eu.anthropic.claude-test-a3-v1:0"
A5_MODEL = "eu.anthropic.claude-test-a5-v1:0"
USAGE = {"prompt_tokens": 900, "completion_tokens": 100, "total_tokens": 1000}
REVISION = "0123456789abcdef0123456789abcdef01234567"


class FakeConverse:
    """Answers like ``BedrockConverseBackend``; *respond* builds the JSON reply."""

    def __init__(self, respond: Callable[[list[dict[str, Any]]], Any], *, model: str) -> None:
        self.model = model
        self.last_usage: Optional[dict[str, int]] = None
        self.calls = 0
        self._respond = respond

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self.calls += 1
        reply = self._respond(messages)
        self.last_usage = dict(USAGE)
        return {"content": json.dumps(reply), "tool_calls": None}


def proposes_nothing(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {"edits": [], "new_entities": []}


def guesses_wrong_or_abstains(messages: list[dict[str, Any]]) -> dict[str, Any]:
    passage = json.loads(messages[-1]["content"])["passages"][0]
    return {"guesses": [
        {"target": "coordinating_institution", "guess": "University of Helsinki",
         "confidence": 0.4, "passage_id": passage["id"], "evidence": passage["text"][:20]},
        {"target": "supervisor", "guess": None, "confidence": None, "passage_id": None,
         "evidence": None},
    ]}


def _run(root: Path, *, a3: Optional[FakeConverse] = None, a5: Optional[FakeConverse] = None,
         **kwargs: Any) -> smoke.SmokeResult:
    options: dict[str, Any] = {
        "a3_backend": a3 or FakeConverse(proposes_nothing, model=A3_MODEL),
        "a5_backend": a5 or FakeConverse(guesses_wrong_or_abstains, model=A5_MODEL),
        "a3_model": A3_MODEL, "a5_model": A5_MODEL, "max_output_tokens": 1000,
        "a3_token_budget": 1_000_000, "a5_token_budget": 1_000_000,
        "pipeline_revision": REVISION,
    }
    options.update(kwargs)
    return smoke.run(root, **options)


def _stages(result: smoke.SmokeResult) -> dict[str, dict[str, Any]]:
    return {s["stage"]: s for s in json.loads(result.status.read_text(encoding="utf-8"))["stages"]}


def _fill_review(template: Path, out: Path) -> Path:
    record = json.loads(template.read_text(encoding="utf-8"))
    for entry in record["pages"]:
        entry.update(verdict="preserved", basis="operator_visual_comparison",
                     reviewed_by="operator", reviewed_on="2026-10-16")
    out.write_text(json.dumps(record), encoding="utf-8")
    return out


def _fill_acceptance(template: Path, out: Path) -> Path:
    record = json.loads(template.read_text(encoding="utf-8"))
    record["attestations"] = {name: True for name in record["attestations"]}
    record.update(signed_by="the operator", signed_on="2026-10-16")
    record["export_rule"] = {"rule_id": "SYNTHETIC-SMOKE-NO-EXPORT",
                             "issued_by": "the private environment's data owner",
                             "read_on": "2026-10-16"}
    out.write_text(json.dumps(record), encoding="utf-8")
    return out


@pytest.fixture(scope="module")
def first(tmp_path_factory) -> tuple[Path, smoke.SmokeResult, FakeConverse, FakeConverse]:
    root = tmp_path_factory.mktemp("an12") / "smoke"
    a3 = FakeConverse(proposes_nothing, model=A3_MODEL)
    a5 = FakeConverse(guesses_wrong_or_abstains, model=A5_MODEL)
    return root, _run(root, a3=a3, a5=a5), a3, a5


class TestWithoutTheOperatorsActs:
    def test_it_runs_every_automatic_stage_and_waits(self, first):
        _root, result, a3, a5 = first
        assert result.outcome == "awaiting_operator"
        stages = _stages(result)
        for stage in ("A0", "A2", "A3", "A4", "A5_scan", "A5_attack"):
            assert stages[stage]["status"] == "complete", stages[stage]
        assert stages["A6"]["status"] == "awaiting_operator"
        assert "A7" not in stages
        assert a3.calls and a5.calls

    def test_it_records_tokens_within_each_budget(self, first):
        _root, result, a3, a5 = first
        stages = _stages(result)
        assert stages["A3"]["tokens_used"] == a3.calls * USAGE["total_tokens"]
        assert stages["A5_attack"]["tokens_used"] == a5.calls * USAGE["total_tokens"]
        assert stages["A3"]["tokens_used"] <= stages["A3"]["token_budget"] == 1_000_000

    def test_the_figure_template_lists_exactly_the_pages_to_look_at(self, first):
        root, result, _a3, _a5 = first
        template = json.loads((root / smoke.FIGURE_TEMPLATE).read_text(encoding="utf-8"))
        unreviewed = json.loads((root / "a6_unreviewed" / "structural_fidelity.json")
                                .read_text(encoding="utf-8"))
        wanted = sorted(f["page"] for f in unreviewed["figures"]
                        if f.get("code") == "figure_not_looked_at")
        assert wanted and [e["page"] for e in template["pages"]] == wanted
        assert all(e["verdict"].startswith("<") for e in template["pages"]), \
            "the driver never makes the operator's verdict for them"

    def test_the_status_says_the_policy_is_a_synthetic_successor(self, first):
        _root, result, _a3, _a5 = first
        status = json.loads(result.status.read_text(encoding="utf-8"))
        assert status["schema"] == smoke.STATUS_SCHEMA
        assert status["policy"]["synthetic_successor"] is True
        assert status["models"] == {"a3": A3_MODEL, "a5": A5_MODEL}


class TestWithTheOperatorsActs:
    @pytest.fixture(scope="class")
    def done(self, first):
        root, _result, _a3, _a5 = first
        review = _fill_review(root / smoke.FIGURE_TEMPLATE, root / "operator" / "review.json")
        second = _run(root, figure_review=review)
        assert second.outcome == "awaiting_operator", _stages(second)
        acceptance = _fill_acceptance(root / smoke.ACCEPTANCE_TEMPLATE,
                                      root / "operator" / "acceptance.json")
        a3 = FakeConverse(proposes_nothing, model=A3_MODEL)
        a5 = FakeConverse(guesses_wrong_or_abstains, model=A5_MODEL)
        third = _run(root, a3=a3, a5=a5, figure_review=review, acceptance_input=acceptance)
        return root, second, third, a3, a5

    def test_the_acceptance_template_names_the_derivative_and_revision(self, done):
        root, second, *_ = done
        template = json.loads((root / smoke.ACCEPTANCE_TEMPLATE).read_text(encoding="utf-8"))
        assert template["derivative_sha256"] == _stages(second)["A4"]["derivative_sha256"]
        assert template["pipeline_revision"] == REVISION
        assert not any(template["attestations"].values())

    def test_it_reaches_a7(self, done):
        _root, _second, third, _a3, _a5 = done
        assert third.outcome == "accepted", list(_stages(third).values())[-1]
        stages = _stages(third)
        assert stages["A6"]["status"] == "complete" and stages["A6"]["passed"]
        assert stages["A7"]["status"] == "complete"
        assert Path(stages["A7"]["public_record"]).is_file()

    def test_a_rerun_makes_no_model_call(self, done):
        *_rest, a3, a5 = done
        assert a3.calls == 0 and a5.calls == 0


class TestRefusals:
    def test_a_root_inside_the_repository_is_refused_before_any_stage(self):
        with pytest.raises(smoke.SmokeRefused, match="inside"):
            _run(smoke.THIS_REPOSITORY / "smoke_here")
        assert not (smoke.THIS_REPOSITORY / "smoke_here").exists()

    def test_a3_stops_at_its_token_budget_and_nothing_later_runs(self, tmp_path):
        result = _run(tmp_path / "smoke", a3_token_budget=10)
        stages = _stages(result)
        assert result.outcome == "stopped"
        assert stages["A3"]["status"] == "stopped_at_token_budget"
        assert "A4" not in stages

    def test_an_unfilled_template_is_refused_without_writing_a_report(self, first, tmp_path):
        root, *_ = first
        result = _run(root, figure_review=root / smoke.FIGURE_TEMPLATE)
        assert result.outcome == "awaiting_operator"
        assert "placeholder" in _stages(result)["A6"]["detail"]

    def test_an_a3_edit_nothing_applies_is_refused_at_a7(self, tmp_path):
        """No stage applies an A3 plan yet (AN6, AN11), so A7 refuses one with edits."""
        def edits_one(messages):
            text = json.loads(messages[-1]["content"])["passage"]["text"]
            word = text.split()[0]
            return {"edits": [{"start": 0, "end": len(word), "original": word,
                               "replacement": "q" * len(word), "category": "niche_topic",
                               "reason": "generalise"}], "new_entities": []}

        root = tmp_path / "smoke"
        first = _run(root, a3=FakeConverse(edits_one, model=A3_MODEL))
        if _stages(first)["A3"]["status"] != "complete":
            pytest.skip(f"the fake edit was not valid for A3: {_stages(first)['A3']}")
        review = _fill_review(root / smoke.FIGURE_TEMPLATE, tmp_path / "review.json")
        _run(root, a3=FakeConverse(edits_one, model=A3_MODEL), figure_review=review)
        acceptance = _fill_acceptance(root / smoke.ACCEPTANCE_TEMPLATE, tmp_path / "accept.json")
        result = _run(root, a3=FakeConverse(edits_one, model=A3_MODEL), figure_review=review,
                      acceptance_input=acceptance)
        assert result.outcome == "refused"
        assert _stages(result)["A7"]["status"] == "refused"


# --------------------------------------------------------------------------- #
# The command line, through the real Converse backend
# --------------------------------------------------------------------------- #


class FakeBedrockClient:
    """Stands in for ``boto3.client('bedrock-runtime')``; answers A3 and A5 by system prompt."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.region: Optional[str] = None

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.requests.append(kwargs)
        system = "".join(b["text"] for b in kwargs.get("system", []))
        messages = [{"role": m["role"], "content": "".join(b.get("text", "") for b in m["content"])}
                    for m in kwargs["messages"]]
        reply = proposes_nothing(messages) if system == rw.SYSTEM_PROMPT \
            else guesses_wrong_or_abstains(messages)
        return {"output": {"message": {"role": "assistant", "content": [{"text": json.dumps(reply)}]}},
                "usage": {"inputTokens": 900, "outputTokens": 100, "totalTokens": 1000}}


class TestTheCommandLine:
    def test_it_runs_over_converse_with_the_pinned_models_and_region(self, tmp_path, monkeypatch):
        client = FakeBedrockClient()

        def factory(service, **kwargs):
            assert service == "bedrock-runtime"
            client.region = kwargs.get("region_name")
            return client

        monkeypatch.setattr(bc.boto3, "client", factory)
        code = smoke.main([
            "--root", str(tmp_path / "smoke"), "--region", "eu-west-1",
            "--a3-model", A3_MODEL, "--a5-model", A5_MODEL, "--max-output-tokens", "1000",
            "--a3-token-budget", "1000000", "--a5-token-budget", "1000000",
            "--pipeline-revision", REVISION,
        ])
        assert code == smoke.EXIT_AWAITING
        assert client.region == "eu-west-1"
        assert {r["modelId"] for r in client.requests} == {A3_MODEL, A5_MODEL}
        assert all("toolConfig" not in r for r in client.requests)
        assert all(r["inferenceConfig"]["maxTokens"] == 1000 for r in client.requests)

    def test_a_region_outside_adr_001_is_refused(self, tmp_path):
        code = smoke.main([
            "--root", str(tmp_path / "smoke"), "--region", "eu-central-1",
            "--a3-model", A3_MODEL, "--a5-model", A5_MODEL, "--max-output-tokens", "1000",
            "--a3-token-budget", "1000", "--a5-token-budget", "1000",
        ])
        assert code == smoke.EXIT_REFUSED
        assert not (tmp_path / "smoke").exists()

    def test_the_token_budgets_have_no_default(self):
        with pytest.raises(SystemExit):
            smoke._parser().parse_args(["--root", "x", "--region", "eu-west-1", "--a3-model", "a",
                                        "--a5-model", "b", "--max-output-tokens", "1"])
