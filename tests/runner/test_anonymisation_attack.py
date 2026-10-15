"""AN8b — closed-book model attack (second half of stage A5).

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN8b:

1. A ``reidentification_report/1`` schema records counts per category, with
   passages kept private.
2. Against a fake backend, a correct guess fails its passage back to A3, and
   wrong or abstained guesses pass.
3. The attack refuses to run with the same model as A3.
4. The report states its limit: a closed-book model is not a motivated human
   expert.

Every model call goes to a fake backend shaped like the runner's
``BedrockConverseBackend``. The derivative is the AN5 derivative of the AN3
fixture. The committed policy leaves the research-group threshold Unresolved,
so the tests attack under a synthetic successor that sets it.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Optional

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import anonymisation_attack as at  # noqa: E402
from runner import anonymisation_intake as ai  # noqa: E402
from runner import anonymisation_policy as ap  # noqa: E402
from runner import anonymisation_redaction as ar  # noqa: E402
from runner import anonymisation_rewrite as rw  # noqa: E402
from tests import _anonymisation_fixture as fx  # noqa: E402

A3_MODEL = "eu.anthropic.claude-test-a3-v1:0"
A5_MODEL = "eu.anthropic.claude-test-a5-v1:0"
NICHE = "cryo-electron tomography of lichen photobionts"
USAGE = {"prompt_tokens": 900, "completion_tokens": 100, "total_tokens": 1000}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# The fake backend
# --------------------------------------------------------------------------- #


def _window(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return json.loads(messages[-1]["content"])


def _guess(target: str, guess: Optional[str], *, passage_id: Optional[str] = None,
           evidence: Optional[str] = None, confidence: Optional[float] = 0.8) -> dict[str, Any]:
    return {"target": target, "guess": guess, "confidence": confidence if guess else None,
            "passage_id": passage_id, "evidence": evidence}


def _niche_passage(messages: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    return next((p for p in _window(messages)["passages"] if NICHE in p["text"]), None)


def names_the_supervisor(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """A correct guess: the niche topic gives the scientific lead away."""
    passage = _niche_passage(messages)
    if passage is None:
        return {"guesses": []}
    return {"guesses": [_guess("supervisor", "Orsolya Vantrell", passage_id=passage["id"],
                               evidence=NICHE)]}


def guesses_wrong_or_abstains(messages: list[dict[str, Any]]) -> dict[str, Any]:
    passage = _niche_passage(messages) or _window(messages)["passages"][0]
    return {"guesses": [
        _guess("coordinating_institution", "University of Helsinki", passage_id=passage["id"],
               evidence=passage["text"][:20]),
        _guess("supervisor", None),
        _guess("country_set", "Finland, Austria, Norway", passage_id=passage["id"],
               evidence=passage["text"][:20]),
    ]}


class FakeConverse:
    """Answers like ``BedrockConverseBackend``; *respond* builds the JSON reply."""

    def __init__(self, respond: Callable[[list[dict[str, Any]]], Any] = names_the_supervisor,
                 *, model: str = A5_MODEL, usage: Optional[dict[str, int]] = None) -> None:
        self.model = model
        self.last_usage: Optional[dict[str, int]] = None
        self.calls: list[list[dict[str, Any]]] = []
        self._respond = respond
        self._usage = dict(USAGE if usage is None else usage)

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self.calls.append(messages)
        reply = self._respond(messages)
        self.last_usage = dict(self._usage)
        content = reply if isinstance(reply, str) else json.dumps(reply)
        return {"content": content, "tool_calls": None}


# --------------------------------------------------------------------------- #
# The world
# --------------------------------------------------------------------------- #


def _resolved_policy_record() -> dict[str, Any]:
    record = copy.deepcopy(ap.load(ap.STARTING_POLICY_PATH).record)
    for target in record["reidentification_threshold"]["targets"]:
        if target["target"] == "research_group":
            target.update(max_correct_guesses=0, declared_status="Assumed",
                          basis="Synthetic test policy: the operator has not set this.")
    return record


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("an8b")
    starting = ap.load(ap.STARTING_POLICY_PATH)
    policy_path = root / "policy.json"
    policy_path.write_text(json.dumps(_resolved_policy_record()), encoding="utf-8")
    policy = ap.load(policy_path)
    built = fx.build(root / "fixture")
    intake = ai.intake(pdf=built.pdf, expected_sha256=_sha(built.pdf), out_dir=root / "intake")
    dictionary = fx.write_dictionary(root / "private")
    redacted = ar.redact(
        pdf=built.pdf, intake_record=intake.intake_record, policy=starting,
        policy_sha256=starting.sha256, dictionary=dictionary,
        dictionary_sha256=ap.policy_sha256(fx.DICTIONARY), out_dir=root / "a2",
    )
    passages = rw.passages(redacted.derivative)
    niche = next(p for p in passages if NICHE in p.text)
    return {"root": root, "policy": policy, "starting": starting,
            "derivative": redacted.derivative, "redaction_log": redacted.edit_log,
            "dictionary": dictionary, "passages": passages, "niche": niche}


def _run(world: dict[str, Any], out: Path, backend: Any, **overrides: Any) -> at.AttackResult:
    kwargs: dict[str, Any] = {
        "derivative": world["derivative"],
        "derivative_sha256": _sha(world["derivative"]),
        "policy": world["policy"],
        "policy_sha256": world["policy"].sha256,
        "dictionary": world["dictionary"],
        "dictionary_sha256": ap.policy_sha256(fx.DICTIONARY),
        "backend": backend,
        "model_id": A5_MODEL,
        "a3_model_id": A3_MODEL,
        "a3_input": world["derivative"],
        "a3_input_sha256": _sha(world["derivative"]),
        "max_output_tokens": 1000,
        "token_budget": 1_000_000,
        "out_dir": out,
    }
    kwargs.update(overrides)
    return at.attack(**kwargs)


def _read(path: Optional[Path]) -> dict[str, Any]:
    assert path is not None
    return json.loads(path.read_text(encoding="utf-8"))


def _target(report: dict[str, Any], name: str) -> dict[str, Any]:
    return next(t for t in report["targets"] if t["target"] == name)


# --------------------------------------------------------------------------- #
# Acceptance 1: the report schema, passages private
# --------------------------------------------------------------------------- #


class TestReport:
    def test_the_report_counts_per_target_and_category(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        result = _run(world, tmp_path / "out", FakeConverse())
        report = _read(result.report)
        assert report["schema"] == "reidentification_report/1"
        assert report["stage"] == "A5"
        assert {t["target"] for t in report["targets"]} == {
            "coordinating_institution", "partner", "supervisor", "project_acronym",
            "country_set", "research_group"}
        supervisor = _target(report, "supervisor")
        assert supervisor["category"] == "person_name"
        assert supervisor["counts"]["correct"] == 1
        assert supervisor["failed"] is True
        assert report["by_category"]["person_name"]["correct"] == 1
        assert report["by_category"]["institution"]["correct"] == 0
        assert report["passages_sent_back"] == 1

    def test_the_report_holds_no_private_text(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        result = _run(world, tmp_path / "out", FakeConverse())
        text = result.report.read_text(encoding="utf-8")  # type: ignore[union-attr]
        for entry in fx.DICTIONARY["entries"]:
            for form in [entry["surface"], *entry["variants"]]:
                assert form not in text
        assert "Vantrell" not in text
        assert NICHE not in text
        for passage in world["passages"]:
            assert f'"{passage.id}"' not in text
        # The details hold the guess and its passage, privately.
        details = result.details.read_text(encoding="utf-8")  # type: ignore[union-attr]
        assert "Orsolya Vantrell" in details
        assert world["niche"].id in details

    def test_every_output_path_inside_the_repository_is_refused(
            self, world: dict[str, Any]) -> None:
        inside = Path(__file__).resolve().parents[2] / ".scratch" / "an8b-out"
        backend = FakeConverse()
        with pytest.raises(ai.IntakeRefused):
            _run(world, inside, backend)
        assert backend.calls == []


# --------------------------------------------------------------------------- #
# Acceptance 2: a correct guess goes back to A3; wrong and abstained pass
# --------------------------------------------------------------------------- #


class TestScoring:
    def test_a_correct_guess_fails_its_passage_back_to_a3(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        result = _run(world, tmp_path / "out", FakeConverse())
        assert result.verdict == "failed"
        flags = _read(result.flags)
        assert flags["schema"] == "anonymisation_a3_flags/1"
        assert flags["derivative_sha256"] == _sha(world["derivative"])
        assert flags["flags"] == {world["niche"].id: ["niche_topic", "person_name"]}

    def test_the_flags_are_accepted_by_the_a3_rewrite(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        result = _run(world, tmp_path / "a5", FakeConverse())
        flags = _read(result.flags)["flags"]

        class NoEdits(FakeConverse):
            def __init__(self) -> None:
                super().__init__(lambda m: {"edits": [], "new_entities": []}, model=A3_MODEL)

        a3 = NoEdits()
        rewritten = rw.rewrite(
            derivative=world["derivative"], redaction_log=world["redaction_log"],
            policy=world["starting"], policy_sha256=world["starting"].sha256,
            dictionary=world["dictionary"], dictionary_sha256=ap.policy_sha256(fx.DICTIONARY),
            flags=flags, backend=a3, model_id=A3_MODEL, max_output_tokens=1000,
            token_budget=1_000_000, out_dir=tmp_path / "a3",
        )
        assert rewritten.status == "complete"
        assert len(a3.calls) == 1

    def test_wrong_and_abstained_guesses_pass(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        result = _run(world, tmp_path / "out", FakeConverse(guesses_wrong_or_abstains))
        assert result.verdict == "passed"
        report = _read(result.report)
        assert _target(report, "coordinating_institution")["counts"]["wrong"] == 1
        assert _target(report, "supervisor")["counts"]["abstained"] == 1
        # A target the model leaves out abstains too.
        assert _target(report, "research_group")["counts"]["abstained"] == 1
        assert _read(result.flags)["flags"] == {}

    def test_a_kept_country_set_may_be_guessed(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        result = _run(world, tmp_path / "out", FakeConverse(guesses_wrong_or_abstains))
        country = _target(_read(result.report), "country_set")
        assert country["guess_admissible"] is True
        assert country["counts"]["admissible"] == 1
        assert country["failed"] is False

    def test_a_correct_guess_under_any_surface_form_counts(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        def initials(messages: list[dict[str, Any]]) -> dict[str, Any]:
            passage = _niche_passage(messages)
            assert passage is not None
            return {"guesses": [_guess("research_group", "Kelpmoor's Department of Cryobiology",
                                       passage_id=passage["id"], evidence=NICHE)]}

        result = _run(world, tmp_path / "out", FakeConverse(initials))
        assert result.verdict == "failed"
        assert _target(_read(result.report), "research_group")["counts"]["correct"] == 1

    def test_a_partial_name_is_listed_for_review_and_does_not_fail(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        def partial(messages: list[dict[str, Any]]) -> dict[str, Any]:
            passage = _niche_passage(messages)
            assert passage is not None
            return {"guesses": [_guess("coordinating_institution", "Kelpmoor Institute",
                                       passage_id=passage["id"], evidence=NICHE)]}

        result = _run(world, tmp_path / "out", FakeConverse(partial))
        assert result.verdict == "passed"
        assert _target(_read(result.report), "coordinating_institution")["counts"]["review"] == 1

    def test_a_correct_guess_on_an_unquoted_passage_fails_without_a_flag(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        def unquoted(messages: list[dict[str, Any]]) -> dict[str, Any]:
            passage = _niche_passage(messages)
            assert passage is not None
            return {"guesses": [_guess("supervisor", "Halvard Quist", passage_id=passage["id"],
                                       evidence="words that are not in the passage")]}

        result = _run(world, tmp_path / "out", FakeConverse(unquoted))
        assert result.verdict == "failed"
        report = _read(result.report)
        assert report["correct_unlocated"] == 1
        assert _read(result.flags)["flags"] == {}

    def test_a_later_stage_s_passage_id_is_mapped_to_a3_s_passage(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        # A later stage adds a line at the top of page 1, so every passage id there shifts.
        later = tmp_path / "later.pdf"
        doc = pymupdf.open(world["derivative"])
        doc[0].insert_text((72, 55), "A heading a later stage added.", fontsize=10)
        doc.save(later)
        doc.close()
        shifted = next(p for p in rw.passages(later) if NICHE in p.text)
        assert shifted.id != world["niche"].id

        result = _run(world, tmp_path / "out", FakeConverse(), derivative=later,
                      derivative_sha256=_sha(later))
        assert _read(result.flags)["flags"] == {world["niche"].id: ["niche_topic", "person_name"]}

    def test_a_repeated_correct_guess_counts_one_entity(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        record = _resolved_policy_record()
        for target in record["reidentification_threshold"]["targets"]:
            if target["target"] == "supervisor":
                target["max_correct_guesses"] = 1
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        tolerant = ap.load(path)

        def twice(messages: list[dict[str, Any]]) -> dict[str, Any]:
            reply = names_the_supervisor(messages)
            return {"guesses": reply["guesses"] * 2}

        result = _run(world, tmp_path / "out", FakeConverse(twice), policy=tolerant,
                      policy_sha256=tolerant.sha256)
        supervisor = _target(_read(result.report), "supervisor")
        assert supervisor["counts"]["correct"] == 2
        assert supervisor["entities_identified"] == 1
        assert supervisor["failed"] is False
        assert result.verdict == "passed"

    def test_a_malformed_reply_leaves_the_verdict_incomplete(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        result = _run(world, tmp_path / "out", FakeConverse(lambda m: "I think it is Kelpmoor."))
        assert result.verdict == "incomplete"
        assert _read(result.report)["windows"]["malformed"] == 1


# --------------------------------------------------------------------------- #
# Acceptance 3: never the A3 model
# --------------------------------------------------------------------------- #


class TestRefusals:
    @pytest.mark.parametrize("a5", [
        A3_MODEL,
        "anthropic.claude-test-a3",
        "arn:aws:bedrock:eu-west-1::foundation-model/anthropic.claude-test-a3-v1:0",
        "us.anthropic.claude-test-a3-v2:0",
    ])
    def test_the_attack_refuses_the_a3_model_in_any_form(
            self, world: dict[str, Any], tmp_path: Path, a5: str) -> None:
        backend = FakeConverse(model=a5)
        with pytest.raises(at.AttackRefused, match="A3"):
            _run(world, tmp_path / "out", backend, model_id=a5)
        assert backend.calls == []

    def test_the_attack_refuses_a_model_outside_the_claude_family(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        other = "eu.meta.llama3-70b-instruct-v1:0"
        backend = FakeConverse(model=other)
        with pytest.raises(at.AttackRefused, match="Claude"):
            _run(world, tmp_path / "out", backend, model_id=other)
        assert backend.calls == []

    def test_a_derivative_with_no_text_is_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        blank = tmp_path / "blank.pdf"
        doc = pymupdf.open()
        doc.new_page()
        doc.save(blank)
        doc.close()
        backend = FakeConverse()
        with pytest.raises(at.AttackRefused, match="no extractable text"):
            _run(world, tmp_path / "out", backend, derivative=blank, derivative_sha256=_sha(blank))
        assert backend.calls == []

    def test_the_backend_must_serve_the_pinned_model(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        backend = FakeConverse(model="eu.anthropic.claude-other")
        with pytest.raises(at.AttackRefused, match="serves"):
            _run(world, tmp_path / "out", backend)
        assert backend.calls == []

    def test_the_attack_is_closed_book(self, world: dict[str, Any], tmp_path: Path) -> None:
        backend = FakeConverse()
        backend._tools = [{"name": "web_search"}]  # type: ignore[attr-defined]
        with pytest.raises(at.AttackRefused, match="closed book"):
            _run(world, tmp_path / "out", backend)
        assert backend.calls == []

    def test_an_unresolved_threshold_refuses_the_run(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        backend = FakeConverse()
        with pytest.raises(at.AttackRefused, match="research_group"):
            _run(world, tmp_path / "out", backend, policy=world["starting"],
                 policy_sha256=world["starting"].sha256)
        assert backend.calls == []

    def test_an_unpinned_derivative_is_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        backend = FakeConverse()
        with pytest.raises(ai.IntakeRefused):
            _run(world, tmp_path / "out", backend, derivative_sha256="0" * 64)
        assert backend.calls == []


# --------------------------------------------------------------------------- #
# Acceptance 4: the limit, and the budget
# --------------------------------------------------------------------------- #


class TestLimitAndBudget:
    def test_the_report_states_its_limit(self, world: dict[str, Any], tmp_path: Path) -> None:
        report = _read(_run(world, tmp_path / "out", FakeConverse()).report)
        assert "closed-book model is not a motivated human expert" in report["limit"]
        assert report["model"]["model_id"] == A5_MODEL
        assert report["model"]["a3_model_id"] == A3_MODEL
        assert report["model"]["tools"] == []

    def test_the_budget_stops_the_attack_and_a_resume_makes_no_repeat_call(
            self, world: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(at, "MAX_WINDOW_CHARS", 400)
        out = tmp_path / "out"
        all_windows = at.windows(world["passages"])
        windows = len(all_windows)
        assert windows >= 3
        one = at.reservation_of(all_windows[0], world["policy"], max_output_tokens=1000)
        # The first call spends its whole reservation, so no second one fits.
        first = FakeConverse(usage={"prompt_tokens": one - 100, "completion_tokens": 100,
                                    "total_tokens": one})
        stopped = _run(world, out, first, token_budget=one + 10)
        assert stopped.status == "stopped_at_token_budget"
        assert stopped.verdict is None and stopped.report is None
        assert len(first.calls) == 1

        second = FakeConverse()
        resumed = _run(world, out, second)
        assert resumed.status == "complete"
        assert resumed.windows_from_checkpoint == 1
        assert len(second.calls) == windows - 1

        third = FakeConverse()
        again = _run(world, out, third)
        assert third.calls == []
        assert again.report.read_bytes() == resumed.report.read_bytes()  # type: ignore[union-attr]
