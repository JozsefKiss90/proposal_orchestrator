"""
The assessor response checkpoint (``harness.response_cache``) and the bounded
re-ask it sits beside.

Two defects are pinned here, both from the run of 2026-10-06 that lost 44
assessor calls to one stray character:

* a sample whose response will not parse is **drawn again**, up to
  :data:`~harness.criterion_scoring.MAX_SAMPLE_REDRAWS`, and every discarded
  draw is recorded on the score — re-asking, never repairing;
* every raw response is checkpointed as it arrives, and a resumed run replays
  those bytes instead of spending quota on them.

Everything runs offline against a scripted backend.  What is pinned:

* a replayed call never reaches the backend, and is byte-identical;
* a checkpoint is bound to its run and refuses to be replayed into another;
* an existing checkpoint is never appended to without ``--resume``;
* an edited checkpoint is refused, not read;
* a malformed response is checkpointed too, so a resume reproduces the run it
  resumes rather than a tidied version of it;
* the report declares replayed and live calls, and says a replay is not a
  fresh draw.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import harness.criterion_scoring as cs
from harness.judge import Judge, JudgeConfig, JudgeError, JudgeResponseError
from harness.provenance import ProvenanceLog, prompt_hash
from harness.response_cache import (
    CHECKPOINT_FORMAT_VERSION,
    CHECKPOINT_HEADER_RECORD_TYPE,
    CacheBinding,
    ResponseCache,
    ResponseCacheError,
    next_checkpoint_path,
)

FROZEN = "2026-10-06T12:00:00+00:00"

BINDING = CacheBinding(
    candidate_hash="sha256:" + "a" * 64,
    profile_version="sha256:" + "b" * 64,
    assessor_pin="fake-assessor@pin-7",
    preflight_pack_set_hash="sha256:" + "c" * 64,
    include_claims=False,
    n=3,
    criterion_samples=5,
)


class CountingBackend:
    """A backend that answers from a script and counts what it was asked."""

    def __init__(self, *contents: str):
        self.contents = list(contents) or ['{"passed": true, "rationale": "ok"}']
        self.calls = 0

    def __call__(self, messages):
        out = self.contents[self.calls % len(self.contents)]
        self.calls += 1
        return {"content": out}


def _judge(tmp_path: Path, backend, cache: ResponseCache | None = None) -> Judge:
    return Judge(
        JudgeConfig(model="fake-assessor", version="pin-7"),
        backend=backend,
        provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
        clock=lambda: FROZEN,
        response_cache=cache,
    )


# --------------------------------------------------------------------------- #
# 1. Recording and replaying
# --------------------------------------------------------------------------- #


class TestRecordAndReplay:
    def test_a_live_call_is_checkpointed_as_it_arrives(self, tmp_path):
        cache = ResponseCache(tmp_path / "ck.jsonl", BINDING, clock=lambda: FROZEN)
        judge = _judge(tmp_path, CountingBackend('{"passed": true, "rationale": "r"}'), cache)

        judge.raw_invoke("system", "user")

        records = [json.loads(l) for l in cache.path.read_text(encoding="utf-8").splitlines()]
        assert records[0]["record_type"] == CHECKPOINT_HEADER_RECORD_TYPE
        assert records[0]["format_version"] == CHECKPOINT_FORMAT_VERSION
        assert records[0]["binding"] == BINDING.to_dict()
        assert records[1]["prompt_hash"] == prompt_hash("system", "user")
        assert records[1]["response"] == '{"passed": true, "rationale": "r"}'
        assert cache.live == 1 and cache.replayed == 0

    def test_a_resumed_call_is_served_from_the_file_and_never_reaches_the_backend(self, tmp_path):
        path = tmp_path / "ck.jsonl"
        first = ResponseCache(path, BINDING, clock=lambda: FROZEN)
        backend = CountingBackend('{"passed": true, "rationale": "first run"}')
        _judge(tmp_path, backend, first).raw_invoke("system", "user")
        assert backend.calls == 1

        resumed = ResponseCache(path, BINDING, resume=True, clock=lambda: FROZEN)
        second = CountingBackend('{"passed": false, "rationale": "must not be asked"}')
        text = _judge(tmp_path, second, resumed).raw_invoke("system", "user")

        assert text == '{"passed": true, "rationale": "first run"}'
        assert second.calls == 0
        assert resumed.replayed == 1 and resumed.live == 0

    def test_samples_of_one_prompt_replay_in_the_order_they_were_drawn(self, tmp_path):
        path = tmp_path / "ck.jsonl"
        cache = ResponseCache(path, BINDING, clock=lambda: FROZEN)
        backend = CountingBackend("one", "two", "three")
        judge = _judge(tmp_path, backend, cache)
        for _ in range(3):
            judge.raw_invoke("system", "user")

        resumed = ResponseCache(path, BINDING, resume=True, clock=lambda: FROZEN)
        replay = _judge(tmp_path, CountingBackend("must not be asked"), resumed)
        assert [replay.raw_invoke("system", "user") for _ in range(3)] == ["one", "two", "three"]

    def test_the_run_goes_live_where_the_checkpoint_runs_out(self, tmp_path):
        path = tmp_path / "ck.jsonl"
        cache = ResponseCache(path, BINDING, clock=lambda: FROZEN)
        _judge(tmp_path, CountingBackend("recorded"), cache).raw_invoke("system", "user")

        resumed = ResponseCache(path, BINDING, resume=True, clock=lambda: FROZEN)
        backend = CountingBackend("live")
        judge = _judge(tmp_path, backend, resumed)
        assert judge.raw_invoke("system", "user") == "recorded"
        assert judge.raw_invoke("system", "user") == "live"
        assert backend.calls == 1
        assert resumed.replayed == 1 and resumed.live == 1
        # The live call joins the same file, so a second resume covers both.
        again = ResponseCache(path, BINDING, resume=True, clock=lambda: FROZEN)
        assert again.replayable == 2

    def test_a_different_prompt_is_not_served_from_another_prompts_record(self, tmp_path):
        path = tmp_path / "ck.jsonl"
        cache = ResponseCache(path, BINDING, clock=lambda: FROZEN)
        _judge(tmp_path, CountingBackend("for prompt A"), cache).raw_invoke("system", "A")

        resumed = ResponseCache(path, BINDING, resume=True, clock=lambda: FROZEN)
        backend = CountingBackend("for prompt B")
        assert _judge(tmp_path, backend, resumed).raw_invoke("system", "B") == "for prompt B"
        assert backend.calls == 1

    def test_a_response_is_checkpointed_before_anything_parses_it(self, tmp_path):
        """The cache sits below the parsers: it records what arrived, as it arrived."""
        path = tmp_path / "ck.jsonl"
        cache = ResponseCache(path, BINDING, clock=lambda: FROZEN)
        broken = '{"score": 4.1, "rationale": "trailing comma", }'
        _judge(tmp_path, CountingBackend(broken), cache).raw_invoke("system", "user")

        resumed = ResponseCache(path, BINDING, resume=True, clock=lambda: FROZEN)
        assert resumed.take(prompt_hash("system", "user")) == broken


# --------------------------------------------------------------------------- #
# 2. Refusals — a checkpoint is bound, and never silently reused
# --------------------------------------------------------------------------- #


class TestRefusals:
    def test_an_existing_file_is_never_appended_to_without_resume(self, tmp_path):
        path = tmp_path / "ck.jsonl"
        ResponseCache(path, BINDING, clock=lambda: FROZEN)
        with pytest.raises(ResponseCacheError, match="already exists"):
            ResponseCache(path, BINDING, clock=lambda: FROZEN)

    def test_resuming_a_missing_file_is_refused(self, tmp_path):
        with pytest.raises(ResponseCacheError, match="nothing to resume"):
            ResponseCache(tmp_path / "absent.jsonl", BINDING, resume=True)

    @pytest.mark.parametrize(
        "field,value",
        [
            ("candidate_hash", "sha256:" + "f" * 64),
            ("profile_version", "sha256:" + "f" * 64),
            ("assessor_pin", "other-assessor@pin-9"),
            ("preflight_pack_set_hash", "sha256:" + "f" * 64),
            ("include_claims", True),
            ("n", 5),
            ("criterion_samples", 3),
        ],
    )
    def test_a_moved_binding_is_refused_and_named(self, tmp_path, field, value):
        path = tmp_path / "ck.jsonl"
        ResponseCache(path, BINDING, clock=lambda: FROZEN)
        import dataclasses

        other = dataclasses.replace(BINDING, **{field: value})
        with pytest.raises(ResponseCacheError, match=field):
            ResponseCache(path, other, resume=True)

    def test_an_edited_response_is_refused(self, tmp_path):
        path = tmp_path / "ck.jsonl"
        cache = ResponseCache(path, BINDING, clock=lambda: FROZEN)
        cache.record(prompt_hash("system", "user"), "the response as given")
        lines = path.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[1])
        record["response"] = "a response nobody gave"
        lines[1] = json.dumps(record)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        with pytest.raises(ResponseCacheError, match="sha256"):
            ResponseCache(path, BINDING, resume=True)

    def test_a_foreign_file_is_refused(self, tmp_path):
        path = tmp_path / "ck.jsonl"
        path.write_text(json.dumps({"record_type": "something.else"}) + "\n", encoding="utf-8")
        with pytest.raises(ResponseCacheError, match="is not a"):
            ResponseCache(path, BINDING, resume=True)

    def test_another_format_version_is_refused(self, tmp_path):
        path = tmp_path / "ck.jsonl"
        path.write_text(
            json.dumps(
                {
                    "record_type": CHECKPOINT_HEADER_RECORD_TYPE,
                    "format_version": CHECKPOINT_FORMAT_VERSION + 1,
                    "binding": BINDING.to_dict(),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ResponseCacheError, match="format version"):
            ResponseCache(path, BINDING, resume=True)

    def test_a_second_cache_on_one_judge_is_refused(self, tmp_path):
        first = ResponseCache(tmp_path / "a.jsonl", BINDING, clock=lambda: FROZEN)
        judge = _judge(tmp_path, CountingBackend(), first)
        with pytest.raises(JudgeError, match="split the run"):
            judge.attach_response_cache(
                ResponseCache(tmp_path / "b.jsonl", BINDING, clock=lambda: FROZEN)
            )

    def test_checkpoint_names_never_collide(self, tmp_path):
        digest = BINDING.candidate_hash
        first = next_checkpoint_path(tmp_path, digest)
        first.write_text("", encoding="utf-8")
        second = next_checkpoint_path(tmp_path, digest)
        assert first.name.endswith("_0001.jsonl") and second.name.endswith("_0002.jsonl")
        assert first != second


# --------------------------------------------------------------------------- #
# 3. The bounded re-ask
# --------------------------------------------------------------------------- #


def _score_json(score: float, *, trailing_comma: bool = False) -> str:
    body = json.dumps(
        {
            "score": score,
            "shortcomings": ["a shortcoming"],
            "strengths": ["a strength"],
            "rationale": "a rationale naming the decisive passage",
        }
    )
    return body[:-1] + ", }" if trailing_comma else body


class TestBoundedReask:
    """``_draw_sample`` asks again; it never mends what came back."""

    def test_the_trailing_comma_that_cost_the_run_is_now_redrawn(self, tmp_path):
        scoring = _scoring()
        backend = CountingBackend(_score_json(4.1, trailing_comma=True), _score_json(4.1))
        sample, discarded = cs._draw_sample(
            _judge(tmp_path, backend), "system", "user", scoring, 0
        )
        assert sample.score == 4.1
        assert backend.calls == 2
        assert [d.attempt for d in discarded] == [0]
        assert "parseable JSON" in discarded[0].reason
        assert discarded[0].response_chars == len(_score_json(4.1, trailing_comma=True))

    def test_nothing_from_a_discarded_draw_reaches_the_sample(self, tmp_path):
        backend = CountingBackend(_score_json(2.0, trailing_comma=True), _score_json(5.0))
        sample, _ = cs._draw_sample(_judge(tmp_path, backend), "system", "user", _scoring(), 0)
        assert sample.score == 5.0

    def test_the_budget_is_bounded_and_the_run_then_fails_closed(self, tmp_path):
        backend = CountingBackend(_score_json(4.1, trailing_comma=True))
        with pytest.raises(JudgeResponseError, match="draw"):
            cs._draw_sample(_judge(tmp_path, backend), "system", "user", _scoring(), 0)
        assert backend.calls == cs.MAX_SAMPLE_REDRAWS + 1

    def test_a_clean_run_records_no_discarded_draw(self, tmp_path):
        backend = CountingBackend(_score_json(4.0))
        _, discarded = cs._draw_sample(_judge(tmp_path, backend), "system", "user", _scoring(), 0)
        assert discarded == [] and backend.calls == 1

    def test_the_prompt_asks_for_strict_json(self, bundle_and_input):
        bundle, criterion_input = bundle_and_input
        system, _user = cs.build_criterion_prompts(bundle, criterion_input)
        assert "No trailing comma" in system




# --------------------------------------------------------------------------- #
# 4. A rejected response is kept, and never replayed
# --------------------------------------------------------------------------- #


class TestDiscardedResponses:
    """Without this, a run could never get past the response that killed it."""

    def test_a_response_the_parsers_rejected_is_not_served_on_resume(self, tmp_path):
        path = tmp_path / "ck.jsonl"
        cache = ResponseCache(path, BINDING, clock=lambda: FROZEN)
        broken = _score_json(4.1, trailing_comma=True)
        judge = _judge(tmp_path, CountingBackend(broken), cache)
        judge.raw_invoke("system", "user")
        cache.discard_last("would not parse")

        resumed = ResponseCache(path, BINDING, resume=True, clock=lambda: FROZEN)
        assert resumed.replayable == 0
        assert resumed.take(prompt_hash("system", "user")) is None

    def test_the_rejected_bytes_stay_in_the_file(self, tmp_path):
        """Kept as the faithful record of what the assessor said, marked unusable."""
        path = tmp_path / "ck.jsonl"
        cache = ResponseCache(path, BINDING, clock=lambda: FROZEN)
        broken = _score_json(4.1, trailing_comma=True)
        _judge(tmp_path, CountingBackend(broken), cache).raw_invoke("system", "user")
        cache.discard_last("would not parse")

        records = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
        assert records[1]["response"] == broken
        assert records[2]["record_type"] == "harness.assessor_response_discarded"
        assert records[2]["reason"] == "would not parse"
        assert records[2]["sha256"] == records[1]["sha256"]

    def test_a_cell_response_evaluate_cannot_parse_is_discarded(self, tmp_path):
        path = tmp_path / "ck.jsonl"
        cache = ResponseCache(path, BINDING, clock=lambda: FROZEN)
        judge = _judge(tmp_path, CountingBackend("not json at all"), cache)
        with pytest.raises(JudgeResponseError):
            judge.evaluate("system", "user", metric="m", property_key="p")

        resumed = ResponseCache(path, BINDING, resume=True, clock=lambda: FROZEN)
        assert resumed.replayable == 0

    def test_a_criterion_draw_that_fails_is_discarded_and_the_good_one_is_kept(self, tmp_path):
        path = tmp_path / "ck.jsonl"
        cache = ResponseCache(path, BINDING, clock=lambda: FROZEN)
        backend = CountingBackend(_score_json(4.1, trailing_comma=True), _score_json(4.1))
        cs._draw_sample(_judge(tmp_path, backend, cache), "system", "user", _scoring(), 0)

        resumed = ResponseCache(path, BINDING, resume=True, clock=lambda: FROZEN)
        assert resumed.replayable == 1
        assert resumed.take(prompt_hash("system", "user")) == _score_json(4.1)

    def test_a_resumed_run_redraws_the_call_that_killed_the_first_one(self, tmp_path):
        """The whole point: the next run spends quota only on what failed."""
        path = tmp_path / "ck.jsonl"
        first = ResponseCache(path, BINDING, clock=lambda: FROZEN)
        broken = CountingBackend(_score_json(4.1, trailing_comma=True))
        with pytest.raises(JudgeResponseError):
            cs._draw_sample(_judge(tmp_path, broken, first), "system", "user", _scoring(), 0)
        assert broken.calls == cs.MAX_SAMPLE_REDRAWS + 1

        resumed = ResponseCache(path, BINDING, resume=True, clock=lambda: FROZEN)
        good = CountingBackend(_score_json(4.1))
        sample, discarded = cs._draw_sample(
            _judge(tmp_path, good, resumed), "system", "user", _scoring(), 0
        )
        assert sample.score == 4.1
        assert good.calls == 1
        assert discarded == []



# --------------------------------------------------------------------------- #
# 5. The command: a run that dies on its last call is resumed, not redrawn
# --------------------------------------------------------------------------- #


class TestTheCommandResumes:
    """The 2026-10-06 failure, end to end: 44 of 45 calls were already paid for."""

    @staticmethod
    def _args(bundle, candidate, out, repo):
        return [
            "assess",
            "--candidate", str(candidate),
            "--out-dir", str(out),
            "--repo-root", str(repo),
            "--profile", str(bundle.profile.source_path),
        ]

    def test_the_run_resumes_and_spends_quota_only_on_what_failed(self, tmp_path):
        import harness.commands.blind_assessment as cmd
        from tests.harness._preflight import preflighted
        from tests.harness.test_blind_assessment import (
            CRITERION_JSON,
            DualBackend,
            _candidate as blind_candidate,
            _synthetic_world as blind_world,
        )
        from harness.rubrics import load_profile_bundle

        repo = tmp_path / "repo"
        world = blind_world(repo)
        bundle = load_profile_bundle(str(world), repo_root=repo)
        candidate = blind_candidate(tmp_path, bundle)
        out = tmp_path / "reports"
        argv = preflighted(self._args(bundle, candidate, out, repo), clock=lambda: FROZEN)

        class DiesOnTheLastCriterionCall(DualBackend):
            """Sound until the final criterion call, then a trailing comma."""

            def __init__(self, fail_from: int):
                super().__init__()
                self.fail_from = fail_from

            def __call__(self, messages):
                out = super().__call__(messages)
                if self.calls >= self.fail_from and out["content"] == CRITERION_JSON:
                    return {"content": CRITERION_JSON[:-1] + ", }"}
                return out

        cells = sum(
            len(bundle.profile.section_ids_for(r.criterion_id))
            for r in bundle.rubric_set.rubrics
        )
        total = cells * 3 + len(bundle.profile.criterion_ids) * 5

        first = DiesOnTheLastCriterionCall(total)
        code = cmd.main(argv, judge=_judge(tmp_path / "a", first), clock=lambda: FROZEN)
        assert code == 2
        assert not out.exists() or not list(out.iterdir())
        # Every draw of the last sample was malformed, so the budget was spent.
        assert first.calls == total + cs.MAX_SAMPLE_REDRAWS

        (checkpoint,) = list((repo / ".harness" / "checkpoints").glob("*.jsonl"))
        second = DualBackend()
        code = cmd.main(
            argv + ["--resume", str(checkpoint)],
            judge=_judge(tmp_path / "b", second),
            clock=lambda: FROZEN,
        )
        assert code == 0
        # One live call: the sample the first run never landed.  The other
        # calls came back from the checkpoint.
        assert second.calls == 1
        (path,) = list(out.iterdir())
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["replayed_calls"] == total - 1
        assert data["live_calls"] == 1
        assert data["checkpoint_path"] == checkpoint.as_posix()
        assert "[NOT a fresh draw]" in __import__(
            "harness.blind_assessment", fromlist=["render_report"]
        ).render_report(data)

    def test_no_checkpoint_writes_none(self, tmp_path):
        import harness.commands.blind_assessment as cmd
        from tests.harness._preflight import preflighted
        from tests.harness.test_blind_assessment import (
            DualBackend,
            _candidate as blind_candidate,
            _synthetic_world as blind_world,
        )
        from harness.rubrics import load_profile_bundle

        repo = tmp_path / "repo"
        world = blind_world(repo)
        bundle = load_profile_bundle(str(world), repo_root=repo)
        out = tmp_path / "reports"
        argv = preflighted(
            self._args(bundle, blind_candidate(tmp_path, bundle), out, repo)
            + ["--no-checkpoint"],
            clock=lambda: FROZEN,
        )
        code = cmd.main(argv, judge=_judge(tmp_path, DualBackend()), clock=lambda: FROZEN)
        assert code == 0
        assert not (repo / ".harness").exists()
        data = json.loads(next(out.iterdir()).read_text(encoding="utf-8"))
        assert data["checkpoint_path"] == "" and data["replayed_calls"] == 0


# --------------------------------------------------------------------------- #
# 6. Salvage: the CLI's own transcripts become a checkpoint
# --------------------------------------------------------------------------- #


def _fake_transcript(path, user: str, response: str) -> None:
    """A ``claude`` CLI session file, shaped as the CLI writes one.

    The user prompt carries CRLF because the transport writes it to the
    child's stdin and the pipe translates; the salvage must undo exactly that.
    """
    lines = [
        {"type": "user", "message": {"role": "user", "content": user.replace("\n", "\r\n")}},
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": response}],
            },
        },
    ]
    path.write_text(
        "".join(json.dumps(l) + "\n" for l in lines), encoding="utf-8"
    )


class TestSalvage:
    """Nothing is guessed: a recorded prompt must equal a rebuilt one exactly."""

    def _world(self, tmp_path):
        from tests.harness.test_blind_assessment import (
            _candidate as blind_candidate,
            _synthetic_world as blind_world,
        )
        from harness.blind_assessment import load_candidate
        from harness.rubrics import load_profile_bundle

        repo = tmp_path / "repo"
        world = blind_world(repo)
        bundle = load_profile_bundle(str(world), repo_root=repo)
        candidate_dir = blind_candidate(tmp_path, bundle)
        candidate = load_candidate(candidate_dir, bundle.profile)
        return repo, bundle, candidate_dir, candidate

    def _cell_prompts(self, bundle, candidate):
        from harness.rubrics import build_pack_for, build_rubric_prompts
        from harness.evidence_pack import (
            DEFAULT_PACK_TOKEN_BUDGET,
            DEFAULT_SPAN_BUDGET_FRACTION,
            MAX_PACK_TOKEN_BUDGET,
        )

        out = []
        for rubric in bundle.rubric_set.rubrics:
            for section_id in bundle.profile.section_ids_for(rubric.criterion_id):
                path = candidate.sections.get(section_id)
                if path is None:
                    continue
                pack = build_pack_for(
                    rubric,
                    path,
                    token_budget=DEFAULT_PACK_TOKEN_BUDGET,
                    span_budget_fraction=DEFAULT_SPAN_BUDGET_FRACTION,
                    max_token_budget=MAX_PACK_TOKEN_BUDGET,
                    include_claims=True,
                )
                out.append(build_rubric_prompts(rubric, pack))
        return out

    def _argv(self, bundle, candidate_dir, repo, out, transcripts, checkpoint):
        from tests.harness._preflight import preflighted

        argv = preflighted(
            [
                "assess",
                "--candidate", str(candidate_dir),
                "--out-dir", str(out),
                "--repo-root", str(repo),
                "--profile", str(bundle.profile.source_path),
            ],
            clock=lambda: FROZEN,
        )
        salvage = ["salvage" if t == "assess" else t for t in argv]
        return argv, salvage + [
            "--transcripts", str(transcripts),
            "--checkpoint", str(checkpoint),
            "--assessor-model", "fake-assessor",
            "--assessor-version", "pin-7",
        ]

    def test_salvaged_cells_replay_and_only_the_criteria_are_redrawn(self, tmp_path):
        import harness.commands.blind_assessment as cmd
        from tests.harness.test_blind_assessment import PASS_JSON, DualBackend

        repo, bundle, candidate_dir, candidate = self._world(tmp_path)
        out, transcripts = tmp_path / "reports", tmp_path / "transcripts"
        transcripts.mkdir()
        checkpoint = tmp_path / "ck.jsonl"

        prompts = self._cell_prompts(bundle, candidate)
        i = 0
        for _system, user in prompts:
            for _sample in range(3):
                _fake_transcript(transcripts / f"{i:04d}.jsonl", user, PASS_JSON)
                i += 1

        argv, salvage_argv = self._argv(
            bundle, candidate_dir, repo, out, transcripts, checkpoint
        )
        assert cmd.main(salvage_argv, clock=lambda: FROZEN) == 0

        backend = DualBackend()
        code = cmd.main(
            argv + ["--resume", str(checkpoint)],
            judge=_judge(tmp_path, backend),
            clock=lambda: FROZEN,
        )
        assert code == 0
        # Every cell came back from the transcripts; only the criteria were drawn.
        assert backend.cell_calls == 0
        assert backend.criterion_calls == 5 * len(bundle.profile.criterion_ids)
        data = json.loads(next(out.iterdir()).read_text(encoding="utf-8"))
        assert data["replayed_calls"] == len(prompts) * 3
        assert data["live_calls"] == backend.criterion_calls

    def test_a_transcript_that_matches_nothing_is_named_and_left_out(self, tmp_path, capsys):
        import harness.commands.blind_assessment as cmd
        from tests.harness.test_blind_assessment import PASS_JSON

        repo, bundle, candidate_dir, candidate = self._world(tmp_path)
        out, transcripts = tmp_path / "reports", tmp_path / "transcripts"
        transcripts.mkdir()
        checkpoint = tmp_path / "ck.jsonl"
        system, user = self._cell_prompts(bundle, candidate)[0]
        _fake_transcript(transcripts / "0000.jsonl", user, PASS_JSON)
        _fake_transcript(transcripts / "0001.jsonl", "a prompt nobody built", PASS_JSON)

        _argv, salvage_argv = self._argv(
            bundle, candidate_dir, repo, out, transcripts, checkpoint
        )
        assert cmd.main(salvage_argv, clock=lambda: FROZEN) == 0
        printed = capsys.readouterr().out
        assert "NOT RECOVERED - 1 transcript(s)" in printed
        assert "0001.jsonl" in printed

        resumed = ResponseCache(
            checkpoint,
            CacheBinding.from_dict(
                json.loads(checkpoint.read_text(encoding="utf-8").splitlines()[0])["binding"]
            ),
            resume=True,
        )
        assert resumed.replayable == 1
        assert resumed.take(prompt_hash(system, user)) == PASS_JSON

    def test_a_recorded_response_that_will_not_parse_is_marked_and_redrawn(self, tmp_path):
        import harness.commands.blind_assessment as cmd

        repo, bundle, candidate_dir, candidate = self._world(tmp_path)
        out, transcripts = tmp_path / "reports", tmp_path / "transcripts"
        transcripts.mkdir()
        checkpoint = tmp_path / "ck.jsonl"
        _system, user = self._cell_prompts(bundle, candidate)[0]
        _fake_transcript(transcripts / "0000.jsonl", user, "not json at all")

        _argv, salvage_argv = self._argv(
            bundle, candidate_dir, repo, out, transcripts, checkpoint
        )
        assert cmd.main(salvage_argv, clock=lambda: FROZEN) == 1
        resumed = ResponseCache(
            checkpoint,
            CacheBinding.from_dict(
                json.loads(checkpoint.read_text(encoding="utf-8").splitlines()[0])["binding"]
            ),
            resume=True,
        )
        assert resumed.replayable == 0

    def test_the_salvaged_binding_equals_the_one_assess_computes(self, tmp_path):
        """A binding that disagreed by one field would refuse the resume."""
        import harness.commands.blind_assessment as cmd
        from tests.harness.test_blind_assessment import PASS_JSON

        repo, bundle, candidate_dir, candidate = self._world(tmp_path)
        out, transcripts = tmp_path / "reports", tmp_path / "transcripts"
        transcripts.mkdir()
        checkpoint = tmp_path / "ck.jsonl"
        _system, user = self._cell_prompts(bundle, candidate)[0]
        _fake_transcript(transcripts / "0000.jsonl", user, PASS_JSON)
        _argv, salvage_argv = self._argv(
            bundle, candidate_dir, repo, out, transcripts, checkpoint
        )
        assert cmd.main(salvage_argv, clock=lambda: FROZEN) == 0

        header = json.loads(checkpoint.read_text(encoding="utf-8").splitlines()[0])
        written = CacheBinding.from_dict(header["binding"])
        assert written.assessor_pin == "fake-assessor@pin-7"
        assert written.n == 3 and written.criterion_samples == 5
        assert written.candidate_hash.startswith("sha256:")
        assert written.preflight_pack_set_hash.startswith("sha256:")


# --------------------------------------------------------------------------- #
# Fixtures: the smallest real scoring block, and one real criterion prompt
# --------------------------------------------------------------------------- #


def _scoring():
    from harness.profile import Scoring

    return Scoring(
        scale="0-5, one decimal place",
        levels={str(i): f"level {i}" for i in range(6)},
        weights={"c": 100.0},
        individual_threshold=3.0,
        overall_threshold=70.0,
        overall_max=100.0,
        score_resolution=0.1,
    )


@pytest.fixture
def bundle_and_input(tmp_path):
    """One real bundle and one complete criterion input, built offline."""
    from tests.harness.test_criterion_scoring import _candidate, _synthetic_world
    from harness.blind_assessment import load_candidate
    from harness.rubrics import load_profile_bundle

    world = _synthetic_world(tmp_path / "world")
    bundle = load_profile_bundle(str(world), repo_root=world.parents[1])
    candidate = load_candidate(_candidate(tmp_path / "cand"), bundle.profile)
    cid = bundle.profile.criterion_ids[0]
    return bundle, cs.build_criterion_input(bundle, candidate, cid)
