"""AN6 — bounded model rewrite (stage A3).

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN6:

1. The validator refuses an edit outside a flagged category, an edit over its
   length budget, and a removal without replacement unless the operator
   approved it.
2. A proposed new entity lands in the operator queue and changes no text.
3. A run interrupted mid-document resumes from its checkpoint without new
   model calls for completed passages.
4. The token budget stops the stage when reached.

Every model call goes to a fake backend shaped like the runner's
``BedrockConverseBackend``: callable with messages, with ``model`` and
``last_usage``. The passages come from the AN5 derivative of the AN3 fixture.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Optional

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import anonymisation_intake as ai  # noqa: E402
from runner import anonymisation_policy as ap  # noqa: E402
from runner import anonymisation_redaction as ar  # noqa: E402
from runner import anonymisation_rewrite as rw  # noqa: E402
from tests import _anonymisation_fixture as fx  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
MODEL = "eu.anthropic.claude-test-a3"
NICHE = "cryo-electron tomography of lichen photobionts in\nhigh-altitude permafrost"
#: Fits the box "cryo-electron ... in" leaves at its line end.
GENERIC = "imaging of symbiotic algae in frozen alpine soils"
USAGE = {"prompt_tokens": 900, "completion_tokens": 100, "total_tokens": 1000}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# The fake backend
# --------------------------------------------------------------------------- #


def _passage_of(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return json.loads(messages[-1]["content"])["passage"]


def _edit(text: str, original: str, replacement: str, category: str = "niche_topic",
          reason: str = "the combination narrows the field to one group") -> dict[str, Any]:
    start = text.index(original)
    return {"start": start, "end": start + len(original), "original": original,
            "replacement": replacement, "category": category, "reason": reason}


def generalise_niche(messages: list[dict[str, Any]]) -> dict[str, Any]:
    text = _passage_of(messages)["text"]
    edits = [_edit(text, NICHE, GENERIC)] if NICHE in text else []
    return {"edits": edits, "new_entities": []}


class FakeConverse:
    """Answers like ``BedrockConverseBackend``; *respond* builds the JSON reply."""

    def __init__(self, respond: Callable[[list[dict[str, Any]]], Any] = generalise_niche, *,
                 model: str = MODEL, usage: Optional[dict[str, int]] = None,
                 fail_on_call: Optional[int] = None) -> None:
        self.model = model
        self.last_usage: Optional[dict[str, int]] = None
        self.calls: list[list[dict[str, Any]]] = []
        self._respond = respond
        self._usage = dict(USAGE if usage is None else usage)
        self._fail_on_call = fail_on_call

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self.calls.append(messages)
        if self._fail_on_call is not None and len(self.calls) == self._fail_on_call:
            raise ConnectionError("the private link dropped")
        reply = self._respond(messages)
        self.last_usage = dict(self._usage)
        content = reply if isinstance(reply, str) else json.dumps(reply)
        return {"content": content, "tool_calls": None}


# --------------------------------------------------------------------------- #
# The world: fixture, intake, A2 derivative
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def policy() -> ap.LoadedPolicy:
    return ap.load(ap.STARTING_POLICY_PATH)


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory, policy: ap.LoadedPolicy) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("an6")
    built = fx.build(root / "fixture")
    intake = ai.intake(pdf=built.pdf, expected_sha256=_sha(built.pdf), out_dir=root / "intake")
    dictionary = fx.write_dictionary(root / "private")
    redacted = ar.redact(
        pdf=built.pdf, intake_record=intake.intake_record, policy=policy,
        policy_sha256=policy.sha256, dictionary=dictionary,
        dictionary_sha256=ap.policy_sha256(fx.DICTIONARY), out_dir=root / "a2",
    )
    passages = rw.passages(redacted.derivative)
    entities = rw.load_pinned_dictionary(dictionary, policy, ap.policy_sha256(fx.DICTIONARY))
    niche = next(p for p in passages if NICHE in p.text)
    return {"root": root, "derivative": redacted.derivative, "redaction_log": redacted.edit_log,
            "dictionary": dictionary, "passages": passages, "entities": entities,
            "niche": niche}


def _run(world: dict[str, Any], policy: ap.LoadedPolicy, out: Path, backend: Any,
         flags: Optional[dict[str, list[str]]] = None, **overrides: Any) -> rw.RewriteResult:
    kwargs: dict[str, Any] = {
        "derivative": world["derivative"],
        "redaction_log": world["redaction_log"],
        "policy": policy,
        "policy_sha256": policy.sha256,
        "dictionary": world["dictionary"],
        "dictionary_sha256": ap.policy_sha256(fx.DICTIONARY),
        "flags": flags if flags is not None else {world["niche"].id: ["niche_topic"]},
        "backend": backend,
        "model_id": MODEL,
        "max_output_tokens": 1000,
        "token_budget": 1_000_000,
        "out_dir": out,
    }
    kwargs.update(overrides)
    return rw.rewrite(**kwargs)


def _plan(result: rw.RewriteResult) -> dict[str, Any]:
    assert result.plan is not None
    return json.loads(result.plan.read_text(encoding="utf-8"))


def _three_flags(world: dict[str, Any]) -> dict[str, list[str]]:
    """The niche passage and two others, one per page, flagged for the rewrite."""
    chosen: dict[int, str] = {}
    for passage in world["passages"]:
        if passage.id == world["niche"].id or passage.page != world["niche"].page:
            chosen.setdefault(passage.page, passage.id)
    chosen[world["niche"].page] = world["niche"].id
    assert len(chosen) == 3
    return {pid: ["niche_topic"] for pid in chosen.values()}


# --------------------------------------------------------------------------- #
# Passages
# --------------------------------------------------------------------------- #


class TestPassages:
    def test_passages_are_bounded_and_in_reading_order(self, world: dict[str, Any]) -> None:
        passages = world["passages"]
        assert len({p.id for p in passages}) == len(passages)
        assert all(len(p.text) <= rw.MAX_PASSAGE_CHARS for p in passages)
        assert all(len(p.text) == len(p.chars) for p in passages)
        # A2's replacement sits in its own block; the passage reads it in place.
        assert "The scientific lead, Prof. Supervisor S01" in world["niche"].text

    def test_the_dictionary_offers_the_niche_passage_as_a_candidate(
            self, world: dict[str, Any]) -> None:
        candidates = rw.candidate_flags(world["passages"], world["entities"])
        assert candidates == {world["niche"].id: ["niche_topic"]}


# --------------------------------------------------------------------------- #
# Acceptance 1: the validator
# --------------------------------------------------------------------------- #


class TestValidator:
    def _validate(self, world: dict[str, Any], policy: ap.LoadedPolicy, edits: list[Any],
                  approved: tuple[rw.RemovalApproval, ...] = ()) -> tuple[list, list]:
        return rw.validate_edits(world["niche"], edits, flagged=("niche_topic",),
                                 policy=policy, dictionary=world["entities"],
                                 approved_removals=approved)

    def test_an_edit_in_a_flagged_category_within_budget_is_accepted(
            self, world: dict[str, Any], policy: ap.LoadedPolicy) -> None:
        accepted, refused = self._validate(world, policy, [_edit(world["niche"].text, NICHE, GENERIC)])
        assert refused == []
        [edit] = accepted
        assert edit["used_points"] <= edit["budget_points"]
        assert [p["replacement"] for p in edit["pieces"]] == [GENERIC, ""]

    def test_an_edit_outside_a_flagged_category_is_refused(
            self, world: dict[str, Any], policy: ap.LoadedPolicy) -> None:
        edit = _edit(world["niche"].text, "Finland", "a Nordic country", category="location")
        accepted, refused = self._validate(world, policy, [edit])
        assert accepted == [] and refused == [{"index": 0, "code": "category_not_flagged"}]

    def test_an_edit_over_its_length_budget_is_refused(
            self, world: dict[str, Any], policy: ap.LoadedPolicy) -> None:
        edit = _edit(world["niche"].text, "permafrost", "ground that stays frozen all year round")
        accepted, refused = self._validate(world, policy, [edit])
        assert accepted == [] and refused == [{"index": 0, "code": "over_length_budget"}]

    def test_a_removal_needs_the_operators_approval(
            self, world: dict[str, Any], policy: ap.LoadedPolicy) -> None:
        edit = _edit(world["niche"].text, NICHE, "")
        assert self._validate(world, policy, [edit]) == (
            [], [{"index": 0, "code": "removal_not_approved"}])
        approval = rw.RemovalApproval(world["niche"].id, edit["start"], edit["end"])
        accepted, refused = self._validate(world, policy, [edit], (approval,))
        assert refused == [] and accepted[0]["removal"] is True

    @pytest.mark.parametrize("change, code", [
        (lambda e: {**e, "end": 10**6}, "span_out_of_bounds"),
        (lambda e: {**e, "original": "something else"}, "span_mismatch"),
        (lambda e: {**e, "reason": " "}, "no_reason"),
        (lambda e: {**e, "replacement": "two\nlines"}, "multiline_replacement"),
        (lambda e: {**e, "replacement": "Halvard Quist"}, "replacement_identifies"),
        (lambda e: {k: v for k, v in e.items() if k != "reason"}, "malformed_edit"),
        (lambda e: {**e, "start": "0"}, "malformed_edit"),
    ])
    def test_other_refusals(self, world: dict[str, Any], policy: ap.LoadedPolicy,
                            change: Callable[[dict], dict], code: str) -> None:
        edit = change(_edit(world["niche"].text, NICHE, GENERIC))
        assert self._validate(world, policy, [edit]) == ([], [{"index": 0, "code": code}])

    def test_overlapping_edits_keep_the_first(
            self, world: dict[str, Any], policy: ap.LoadedPolicy) -> None:
        text = world["niche"].text
        accepted, refused = self._validate(world, policy, [
            _edit(text, NICHE, GENERIC), _edit(text, "permafrost", "soil")])
        assert len(accepted) == 1 and refused == [{"index": 1, "code": "overlap"}]

    def test_a_category_the_policy_reserves_for_the_operator_cannot_be_flagged(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        with pytest.raises(rw.RewriteRefused, match="identifying_figure"):
            _run(world, policy, tmp_path / "out", FakeConverse(),
                 flags={world["niche"].id: ["identifying_figure"]})


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #


class TestRun:
    def test_a_run_writes_a_validated_plan_one_call_per_flagged_passage(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        backend = FakeConverse()
        result = _run(world, policy, tmp_path / "out", backend)
        assert result.status == "complete" and result.calls_made == 1
        plan = _plan(result)
        assert plan["stage"] == "A3" and plan["model"]["model_id"] == MODEL
        assert plan["applied"] is False
        [passage] = plan["passages"]
        assert passage["id"] == world["niche"].id and passage["response_status"] == "valid"
        assert [e["replacement"] for e in passage["edits"]] == [GENERIC]
        # Only the passage and the flagged categories' rules went to the model.
        [messages] = backend.calls
        sent = json.loads(messages[-1]["content"])
        assert sent["passage"]["text"] == world["niche"].text
        assert [c["id"] for c in sent["policy"]["categories"]] == ["niche_topic"]
        assert all(m["role"] in ("system", "user") for m in messages)

    def test_same_inputs_give_the_same_plan_bytes(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        one = _run(world, policy, tmp_path / "one", FakeConverse())
        two = _run(world, policy, tmp_path / "two", FakeConverse())
        assert one.plan is not None and two.plan is not None
        assert one.plan.read_bytes() == two.plan.read_bytes()

    def test_a_malformed_response_is_recorded_not_repaired(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        reply = "```json\n" + json.dumps({"edits": [], "new_entities": []}) + "\n```"
        result = _run(world, policy, tmp_path / "out", FakeConverse(lambda m: reply))
        [passage] = _plan(result)["passages"]
        assert passage["response_status"] == "malformed" and passage["edits"] == []

    @pytest.mark.parametrize("override, match", [
        ({"model_id": "eu.anthropic.other"}, "model"),
        ({"token_budget": 0}, "token budget"),
        ({"flags": {"p9-9": ["niche_topic"]}}, "p9-9"),
        ({"flags": {}}, "flag"),
        ({"policy_sha256": "0" * 64}, "policy"),
        ({"dictionary_sha256": "0" * 64}, "dictionary"),
    ])
    def test_setup_refusals(self, world: dict[str, Any], policy: ap.LoadedPolicy,
                            tmp_path: Path, override: dict[str, Any], match: str) -> None:
        backend = FakeConverse()
        with pytest.raises((rw.RewriteRefused, ap.PolicyChanged), match=match):
            _run(world, policy, tmp_path / "out", backend, **override)
        assert backend.calls == []

    def test_a_backend_with_tools_is_refused(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        backend = FakeConverse()
        backend._tools = [{"type": "function"}]  # type: ignore[attr-defined]
        with pytest.raises(rw.RewriteRefused, match="tools"):
            _run(world, policy, tmp_path / "out", backend)

    def test_a_derivative_the_redaction_log_did_not_write_is_refused(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        other = tmp_path / "other.pdf"
        other.write_bytes(world["derivative"].read_bytes() + b"\n")
        with pytest.raises(ai.IntakeRefused, match="not the pinned file"):
            _run(world, policy, tmp_path / "out", FakeConverse(), derivative=other)

    def test_a_private_path_inside_the_repository_is_refused(
            self, world: dict[str, Any], policy: ap.LoadedPolicy) -> None:
        with pytest.raises(ai.IntakeRefused, match="inside this repository"):
            _run(world, policy, REPO / ".scratch" / "an6_out", FakeConverse())
        assert not (REPO / ".scratch" / "an6_out").exists()


# --------------------------------------------------------------------------- #
# Acceptance 2: the operator queue
# --------------------------------------------------------------------------- #


class TestOperatorQueue:
    ENTITY = "Supervisory Board"

    def test_a_proposed_entity_is_queued_and_changes_no_text(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        assert self.ENTITY in world["niche"].text

        def propose(messages: list[dict[str, Any]]) -> dict[str, Any]:
            reply = generalise_niche(messages)
            reply["new_entities"] = [
                {"text": self.ENTITY, "category": "institution",
                 "reason": "a named body the dictionary lacks"},
                {"text": "something", "category": "not_a_category", "reason": "x"},
            ]
            return reply

        result = _run(world, policy, tmp_path / "out", FakeConverse(propose))
        without = _run(world, policy, tmp_path / "without", FakeConverse())
        [passage] = _plan(result)["passages"]
        [baseline] = _plan(without)["passages"]
        # The plan's edits are those of a run with no proposal: nothing touches the entity.
        assert passage["edits"] == baseline["edits"]
        assert all(not (e["start"] < world["niche"].text.index(self.ENTITY) + len(self.ENTITY)
                        and world["niche"].text.index(self.ENTITY) < e["end"])
                   for e in passage["edits"])
        assert passage["proposals"] == 1 and passage["malformed_proposals"] == 1
        assert result.queue is not None
        queue = json.loads(result.queue.read_text(encoding="utf-8"))
        assert queue["applied"] is False
        assert queue["proposals"] == [{
            "passage_id": world["niche"].id, "text": self.ENTITY,
            "category": "institution", "reason": "a named body the dictionary lacks",
            "status": "awaiting_operator",
        }]
        # The dictionary on disk is untouched.
        assert json.loads(world["dictionary"].read_text(encoding="utf-8")) == fx.DICTIONARY


# --------------------------------------------------------------------------- #
# Acceptance 3: resume from the checkpoint
# --------------------------------------------------------------------------- #


class TestResume:
    def test_an_interrupted_run_resumes_without_redrawing(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        flags = _three_flags(world)
        out = tmp_path / "out"
        with pytest.raises(ConnectionError):
            _run(world, policy, out, FakeConverse(fail_on_call=3), flags=flags)
        assert len(list((out / rw.CHECKPOINT_DIR).glob("*.json"))) == 2
        assert not (out / rw.PLAN_FILE).exists()

        resumed = FakeConverse()
        result = _run(world, policy, out, resumed, flags=flags)
        assert result.status == "complete" and len(resumed.calls) == 1
        assert result.calls_made == 1 and result.passages_from_checkpoint == 2

        fresh = _run(world, policy, tmp_path / "fresh", FakeConverse(), flags=flags)
        assert result.plan is not None and fresh.plan is not None
        assert result.plan.read_bytes() == fresh.plan.read_bytes()

    def test_a_completed_run_makes_no_call_when_run_again(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        out = tmp_path / "out"
        first = _run(world, policy, out, FakeConverse())
        again = FakeConverse()
        second = _run(world, policy, out, again)
        assert again.calls == [] and first.plan == second.plan

    def test_an_approved_removal_is_revalidated_without_a_call(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        def remove(messages: list[dict[str, Any]]) -> dict[str, Any]:
            return {"edits": [_edit(_passage_of(messages)["text"], NICHE, "")],
                    "new_entities": []}

        out = tmp_path / "out"
        first = _run(world, policy, out, FakeConverse(remove))
        [passage] = _plan(first)["passages"]
        assert passage["refused"] == [{"index": 0, "code": "removal_not_approved"}]

        start = world["niche"].text.index(NICHE)
        approval = rw.RemovalApproval(world["niche"].id, start, start + len(NICHE))
        again = FakeConverse(remove)
        second = _run(world, policy, out, again, approved_removals=(approval,))
        assert again.calls == []
        [passage] = _plan(second)["passages"]
        assert passage["refused"] == [] and passage["edits"][0]["removal"] is True

    def test_a_checkpoint_missing_a_field_is_refused(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        out = tmp_path / "out"
        _run(world, policy, out, FakeConverse())
        [path] = (out / rw.CHECKPOINT_DIR).glob("*.json")
        record = json.loads(path.read_text(encoding="utf-8"))
        del record["tokens_charged"]
        path.write_text(json.dumps(record), encoding="utf-8")
        with pytest.raises(rw.RewriteRefused, match="lacks a field"):
            _run(world, policy, out, FakeConverse())

    def test_a_checkpoint_from_other_inputs_is_refused(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        out = tmp_path / "out"
        _run(world, policy, out, FakeConverse())
        other = FakeConverse(model="eu.anthropic.other")
        with pytest.raises(rw.RewriteRefused, match="checkpoint"):
            _run(world, policy, out, other, model_id="eu.anthropic.other")
        assert other.calls == []


# --------------------------------------------------------------------------- #
# Acceptance 4: the token budget
# --------------------------------------------------------------------------- #


class TestTokenBudget:
    def test_the_budget_stops_the_stage_and_a_larger_one_resumes_it(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        flags = _three_flags(world)
        out = tmp_path / "out"
        usage = {"prompt_tokens": 1500, "completion_tokens": 500, "total_tokens": 2000}
        probe = FakeConverse(usage=usage)
        _run(world, policy, tmp_path / "probe", probe, flags=flags)
        reserves = [rw.reservation(m, max_output_tokens=1000) for m in probe.calls]
        # Room for the first call, and not for whichever call could come second.
        budget = usage["total_tokens"] + min(reserves[1:]) - 1
        assert reserves[0] <= budget

        backend = FakeConverse(usage=usage)
        stopped = _run(world, policy, out, backend, flags=flags, token_budget=budget)
        assert stopped.status == "stopped_at_token_budget"
        assert len(backend.calls) == 1 and stopped.plan is None
        assert stopped.tokens_used == usage["total_tokens"] and stopped.passages_pending == 2

        resumed = FakeConverse(usage=usage)
        done = _run(world, policy, out, resumed, flags=flags, token_budget=10**6)
        assert done.status == "complete" and len(resumed.calls) == 2
        assert done.tokens_used == 3 * usage["total_tokens"]

    def test_a_budget_below_the_first_reservation_makes_no_call(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        backend = FakeConverse()
        result = _run(world, policy, tmp_path / "out", backend, token_budget=100)
        assert result.status == "stopped_at_token_budget" and backend.calls == []

    def test_a_reply_longer_than_the_declared_limit_stops_the_run(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        backend = FakeConverse(usage={"prompt_tokens": 10, "completion_tokens": 2000,
                                      "total_tokens": 2010})
        out = tmp_path / "out"
        with pytest.raises(rw.RewriteRefused, match="max_output_tokens"):
            _run(world, policy, out, backend)
        # The checkpointed overspend refuses every resume too.
        again = FakeConverse()
        with pytest.raises(rw.RewriteRefused, match="reservation"):
            _run(world, policy, out, again)
        assert again.calls == []

    def test_a_call_with_no_reported_usage_is_charged_its_reservation(
            self, world: dict[str, Any], policy: ap.LoadedPolicy, tmp_path: Path) -> None:
        class Stale(FakeConverse):
            """Like BedrockConverseBackend: a reply without usage keeps the last call's."""

            def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
                previous = self.last_usage
                reply = super().__call__(messages)
                if len(self.calls) > 1:
                    self.last_usage = previous
                return reply

        backend = Stale()
        result = _run(world, policy, tmp_path / "out", backend, flags=_three_flags(world))
        later = [rw.reservation(m, max_output_tokens=1000) for m in backend.calls[1:]]
        assert result.tokens_used == USAGE["total_tokens"] + sum(later)

    def test_the_reservation_is_an_upper_bound_on_the_request(self) -> None:
        messages = [{"role": "system", "content": "ab"}, {"role": "user", "content": "é"}]
        assert rw.reservation(messages, max_output_tokens=10) == (
            2 + 2 + rw.REQUEST_OVERHEAD_TOKENS + 10)


# --------------------------------------------------------------------------- #
# The Converse builder
# --------------------------------------------------------------------------- #


class TestConverseBuilder:
    def test_the_builder_pins_model_temperature_tokens_and_no_tools(
            self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: dict[str, Any] = {}

        class Recorder:
            def __init__(self, **kwargs: Any) -> None:
                seen.update(kwargs)

        from runner.transport import bedrock_converse

        monkeypatch.setattr(bedrock_converse, "BedrockConverseBackend", Recorder)
        rw.build_converse_backend(model_id=MODEL, region="eu-west-1", max_output_tokens=1000)
        assert seen == {"model_id": MODEL, "region_name": "eu-west-1", "temperature": 0.0,
                        "max_tokens": 1000}

    def test_a_region_outside_adr_001_is_refused(self) -> None:
        with pytest.raises(rw.RewriteRefused, match="region"):
            rw.build_converse_backend(model_id=MODEL, region="eu-central-1",
                                      max_output_tokens=1000)
