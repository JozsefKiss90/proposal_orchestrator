"""AN11 — acceptance records and the written export procedure (stage A7).

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN11:

1. A test asserts that the public record contains no private content.
2. The public record refuses to build unless the leak scan and attack both
   passed and the fidelity findings are all explained.
3. The written export procedure names each step and the rule that permits it.

The world runs every stage before A7 on the AN3 synthetic fixture, outside the
repository: A0 intake, A2 redaction, A3 rewrite, A4 table synthesis, A6
structural fidelity and both halves of A5. Model stages answer from fake
backends. The committed policy leaves the research-group threshold
Unresolved, so every stage runs under a synthetic successor that sets it, as
the AN8b tests do.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Optional

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import anonymisation_acceptance as aa  # noqa: E402
from runner import anonymisation_attack as atk  # noqa: E402
from runner import anonymisation_fidelity as af  # noqa: E402
from runner import anonymisation_intake as ai  # noqa: E402
from runner import anonymisation_leak_scan as ls  # noqa: E402
from runner import anonymisation_matching as matching  # noqa: E402
from runner import anonymisation_policy as ap  # noqa: E402
from runner import anonymisation_redaction as ar  # noqa: E402
from runner import anonymisation_rewrite as rw  # noqa: E402
from runner import anonymisation_table as at  # noqa: E402
from tests import _anonymisation_fixture as fx  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

A3_MODEL = "eu.anthropic.claude-test-a3-v1:0"
A5_MODEL = "eu.anthropic.claude-test-a5-v1:0"
NICHE = "cryo-electron tomography of lichen photobionts"
USAGE = {"prompt_tokens": 900, "completion_tokens": 100, "total_tokens": 1000}
#: Plainly synthetic: a test must not look like it names a real commit.
PIPELINE_REVISION = "0123456789abcdef0123456789abcdef01234567"
GRAPHICAL_PAGES = [1, 2, 3]
DICTIONARY_SHA256 = ap.policy_sha256(fx.DICTIONARY)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Fake backends
# --------------------------------------------------------------------------- #


class FakeConverse:
    """Answers like ``BedrockConverseBackend``; *respond* builds the JSON reply."""

    def __init__(self, respond: Callable[[list[dict[str, Any]]], Any], *, model: str) -> None:
        self.model = model
        self.last_usage: Optional[dict[str, int]] = None
        self._respond = respond

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
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


# --------------------------------------------------------------------------- #
# The world: every stage before A7, under one private root
# --------------------------------------------------------------------------- #


def _resolved_policy_record() -> dict[str, Any]:
    record = copy.deepcopy(ap.load(ap.STARTING_POLICY_PATH).record)
    for target in record["reidentification_threshold"]["targets"]:
        if target["target"] == "research_group":
            target.update(max_correct_guesses=0, declared_status="Assumed",
                          basis="Synthetic test policy: the operator has not set this.")
    return record


def _operator_input(derivative_sha256: str, **changes: Any) -> dict[str, Any]:
    record = {
        "schema": aa.INPUT_SCHEMA,
        "record_type": aa.INPUT_RECORD_TYPE,
        "derivative_sha256": derivative_sha256,
        "decision": "accept",
        "attestations": {name: True for name in aa.ATTESTATIONS},
        "signed_by": "the operator",
        "signed_on": "2026-10-16",
        "pipeline_revision": PIPELINE_REVISION,
        "export_rule": {
            "rule_id": "PRIVATE-ENV-EXPORT-RULE-FIXTURE",
            "issued_by": "the private environment's data owner",
            "read_on": "2026-10-16",
        },
    }
    record.update(changes)
    return record


def _write_json(path: Path, record: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("an11")
    policy_path = _write_json(root / "policy" / "policy.json", _resolved_policy_record())
    policy = ap.load(policy_path)
    private = root / "private"
    dictionary = fx.write_dictionary(private)

    built = fx.build(root / "fixture")
    intake = ai.intake(pdf=built.pdf, expected_sha256=_sha(built.pdf), out_dir=root / "a0")
    redacted = ar.redact(
        pdf=built.pdf, intake_record=intake.intake_record, policy=policy,
        policy_sha256=policy.sha256, dictionary=dictionary,
        dictionary_sha256=DICTIONARY_SHA256, out_dir=root / "a2",
    )
    niche = next(p for p in rw.passages(redacted.derivative) if NICHE in p.text)
    rewritten = rw.rewrite(
        derivative=redacted.derivative, redaction_log=redacted.edit_log, policy=policy,
        policy_sha256=policy.sha256, dictionary=dictionary,
        dictionary_sha256=DICTIONARY_SHA256, flags={niche.id: ["niche_topic"]},
        backend=FakeConverse(proposes_nothing, model=A3_MODEL), model_id=A3_MODEL,
        max_output_tokens=1000, token_budget=1_000_000, out_dir=root / "a3",
    )
    assert rewritten.status == "complete"
    synthesised = at.synthesise(
        derivative=redacted.derivative, redaction_log=redacted.edit_log,
        intake_record=intake.intake_record, policy=policy, policy_sha256=policy.sha256,
        dictionary=dictionary, dictionary_sha256=DICTIONARY_SHA256,
        spec=fx.write_table_spec(private), spec_sha256=ap.policy_sha256(fx.TABLE_SPEC),
        out_dir=root / "a4",
    )
    derivative = synthesised.derivative
    review = _write_json(root / "a6_review" / "figure_review.json", {
        "schema": af.REVIEW_SCHEMA,
        "record_type": af.REVIEW_RECORD_TYPE,
        "derivative_sha256": synthesised.derivative_sha256,
        "pages": [
            {"page": p, "verdict": "preserved", "basis": "operator_visual_comparison",
             "reviewed_by": "operator", "reviewed_on": "2026-10-16", "note": ""}
            for p in GRAPHICAL_PAGES
        ],
    })
    fidelity = af.fidelity(
        derivative=derivative, derivative_sha256=synthesised.derivative_sha256,
        intake_record=intake.intake_record, policy=policy, policy_sha256=policy.sha256,
        stage_logs=[redacted.edit_log, synthesised.log], figure_review=review,
        out_dir=root / "a6",
    )
    assert fidelity.passed
    scan = ls.leak_scan(derivative=derivative, policy=policy, policy_sha256=policy.sha256,
                        dictionary=dictionary, dictionary_sha256=DICTIONARY_SHA256,
                        out_dir=root / "a5_scan")
    assert scan.passed
    attack = atk.attack(
        derivative=derivative, derivative_sha256=synthesised.derivative_sha256, policy=policy,
        policy_sha256=policy.sha256, dictionary=dictionary,
        dictionary_sha256=DICTIONARY_SHA256,
        backend=FakeConverse(guesses_wrong_or_abstains, model=A5_MODEL), model_id=A5_MODEL,
        a3_model_id=A3_MODEL, a3_input=redacted.derivative,
        a3_input_sha256=_sha(redacted.derivative), max_output_tokens=1000,
        token_budget=1_000_000, out_dir=root / "a5_attack",
    )
    assert attack.verdict == "passed"
    operator = _write_json(root / "a7_input" / "acceptance_input.json",
                           _operator_input(synthesised.derivative_sha256))
    return {
        "root": root, "policy": policy, "dictionary": dictionary, "derivative": derivative,
        "derivative_sha256": synthesised.derivative_sha256,
        "stage_logs": [redacted.edit_log, synthesised.log], "row_map": synthesised.row_map,
        "rewrite_plan": rewritten.plan, "fidelity": fidelity.report, "leak_scan": scan.report,
        "attack": attack.report, "attack_details": attack.details, "operator": operator,
        "source": built.pdf,
    }


def _accept(world: dict[str, Any], out: Path, **overrides: Any) -> aa.AcceptanceResult:
    kwargs: dict[str, Any] = {
        "derivative": world["derivative"],
        "derivative_sha256": world["derivative_sha256"],
        "policy": world["policy"],
        "policy_sha256": world["policy"].sha256,
        "dictionary": world["dictionary"],
        "dictionary_sha256": DICTIONARY_SHA256,
        "stage_logs": world["stage_logs"],
        "table_row_map": world["row_map"],
        "rewrite_plan": world["rewrite_plan"],
        "structural_fidelity": world["fidelity"],
        "leak_scan": world["leak_scan"],
        "reidentification_report": world["attack"],
        "reidentification_details": world["attack_details"],
        "operator_input": world["operator"],
        "out_dir": out,
    }
    kwargs.update(overrides)
    return aa.accept(**kwargs)


@pytest.fixture(scope="module")
def accepted(world: dict[str, Any]) -> aa.AcceptanceResult:
    return _accept(world, world["root"] / "a7")


@pytest.fixture(scope="module")
def entities(world: dict[str, Any]) -> matching.EntityDictionary:
    return matching.load_dictionary(world["dictionary"], world["policy"])


def _tampered(world: dict[str, Any], tmp: Path, source: Path, change: Callable[[dict], None]
              ) -> Path:
    record = _read(source)
    change(record)
    return _write_json(tmp / "tampered" / source.name, record)


# --------------------------------------------------------------------------- #
# The two records
# --------------------------------------------------------------------------- #


class TestRecords:
    def test_acceptance_writes_a_private_and_a_public_record(
            self, accepted: aa.AcceptanceResult) -> None:
        private = _read(accepted.private_record)
        public = _read(accepted.public_record)
        assert private["schema"] == aa.SCHEMA
        assert public["schema"] == aa.PUBLIC_SCHEMA
        assert public["record_type"] == "decision_record"
        assert public == accepted.public
        assert public["private_record_sha256"] == _sha(accepted.private_record)

    def test_the_private_record_holds_the_full_acceptance(
            self, world: dict[str, Any], accepted: aa.AcceptanceResult) -> None:
        private = _read(accepted.private_record)
        mapping = private["mapping_table"]
        assert mapping["dictionary_sha256"] == DICTIONARY_SHA256
        assert mapping["table_row_map_sha256"] == _sha(world["row_map"])
        assert [e["sha256"] for e in mapping["edit_logs"]] == [
            _sha(p) for p in world["stage_logs"]]
        assert re.fullmatch(r"[0-9a-f]{64}", mapping["sha256"])
        details = private["reidentification"]["details"]
        assert details["reidentification_details_sha256"] == _sha(world["attack_details"])
        assert details["leak_scan_report_sha256"] == _sha(world["leak_scan"])
        assert private["operator"]["input_sha256"] == _sha(world["operator"])

    def test_the_public_record_holds_the_metadata_the_handoff_names(
            self, world: dict[str, Any], accepted: aa.AcceptanceResult) -> None:
        public = accepted.public
        assert public["derivative"]["sha256"] == world["derivative_sha256"]
        assert public["policy"] == {
            "policy_id": world["policy"].record["policy_id"],
            "policy_version": world["policy"].version,
            "sha256": world["policy"].sha256,
        }
        assert public["pipeline_revision"]["commit"] == PIPELINE_REVISION
        assert public["pipeline_revision"]["declared_status"] == "Assumed"
        a5 = public["a5_reidentification"]
        assert a5["leak_scan"]["verdict"] == "pass"
        assert set(a5["leak_scan"]["counts"]) == {"hits", "review"}
        assert a5["model_attack"]["verdict"] == "passed"
        assert "person_name" in a5["model_attack"]["by_category"]
        assert set(public["a6_structural_fidelity"]["counts"]) == set(af.CATEGORIES)
        assert public["models"]["a3"]["model_id"] == A3_MODEL
        assert public["models"]["a5"]["model_id"] == A5_MODEL
        assert public["operator_signature"]["signed_by"] == "the operator"
        assert public["operator_signature"]["signed_on"] == "2026-10-16"
        assert public["export_rule"]["rule_id"] == "PRIVATE-ENV-EXPORT-RULE-FIXTURE"
        assert public["export_rule"]["declared_status"] == "Assumed"

    def test_the_public_record_is_the_one_the_j0_d3_condition_points_to(
            self, accepted: aa.AcceptanceResult) -> None:
        condition = accepted.public["d3_condition"]
        assert condition["record"] == aa.J0_RECORD_ID
        assert (REPO / aa.J0_RECORD_REL).is_file()
        j0 = _read(REPO / aa.J0_RECORD_REL)
        assert any(c["class"] == "D3" for c in j0["data_classes"])
        assert [part["part"] for part in condition["parts"]] == list(aa.D3_CONDITION_PARTS)
        for part in condition["parts"]:
            assert part["declared_status"] in {"Confirmed", "Inferred", "Assumed"}
            assert part["basis"]

    def test_a_rerun_is_a_no_op_and_a_different_record_is_never_written_over(
            self, world: dict[str, Any], accepted: aa.AcceptanceResult, tmp_path: Path) -> None:
        before = accepted.private_record.read_bytes()
        again = _accept(world, accepted.private_record.parent)
        assert again.private_record.read_bytes() == before
        other = _write_json(tmp_path / "input.json",
                            _operator_input(world["derivative_sha256"], signed_on="2026-10-17"))
        with pytest.raises(aa.AcceptanceRefused, match="never overwritten"):
            _accept(world, accepted.private_record.parent, operator_input=other)


# --------------------------------------------------------------------------- #
# Acceptance 1: the public record holds no private content
# --------------------------------------------------------------------------- #


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for k, v in value.items() for s in (k, *_strings(v))]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


class TestNoPrivateContent:
    def test_no_dictionary_form_appears_in_the_public_record(
            self, accepted: aa.AcceptanceResult) -> None:
        text = accepted.public_record.read_text(encoding="utf-8").casefold()
        for entry in fx.DICTIONARY["entries"]:
            if entry["category"] == "location":
                continue  # the policy keeps countries
            for form in [entry["surface"], *entry["variants"]]:
                assert form.casefold() not in text, entry["id"]
            person = entry.get("person")
            if person:
                assert person["family"].casefold() not in text, entry["id"]

    def test_no_planted_text_appears_in_the_public_record(
            self, accepted: aa.AcceptanceResult) -> None:
        text = accepted.public_record.read_text(encoding="utf-8")
        for entity in fx.ENTITIES:
            if entity["invented"] is False:
                continue
            assert entity["surface"] not in text, entity["id"]
            for planting in entity["plantings"]:
                planted = planting.get("text")
                # A bare number, such as a table metric, is also a count or a hash digit.
                if planted and not planted.replace(".", "").isdigit():
                    assert planted not in text, entity["id"]

    def test_the_dictionary_matcher_finds_nothing_in_the_public_record(
            self, accepted: aa.AcceptanceResult, entities: matching.EntityDictionary) -> None:
        for string in _strings(accepted.public):
            if aa.is_digest(string):
                continue  # one-way; see test_a_digest_is_not_read_as_an_identifier
            assert not matching.find_matches(string, entities), string

    def test_a_digest_is_not_read_as_an_identifier(
            self, entities: matching.EntityDictionary) -> None:
        """AN12: a smoke run's policy hash began 579423577c, which the grant number
        pattern matched, and A7 refused a clean derivative."""
        digest = "579423577cbe07e4363e75178f402e224bcc2174a5d8e403090edf533c74fe23"
        assert matching.find_matches(digest, entities), "the pattern does match the digest"
        aa._refuse_entities({"policy_sha256": digest, "pipeline_revision": digest[:40]},
                            entities)

    def test_a_bare_identifier_is_still_refused(
            self, entities: matching.EntityDictionary) -> None:
        with pytest.raises(aa.AcceptanceRefused, match="grant_number"):
            aa._refuse_entities({"signed_by": "579423577"}, entities)
        with pytest.raises(aa.AcceptanceRefused):
            aa._refuse_entities({"signed_by": "579423577cbe07e4363e75178f402e224bcc2174a5d8e40"
                                              "3090edf533c74fe23 579423577"}, entities)

    def test_the_public_record_names_no_file_and_no_private_path(
            self, world: dict[str, Any], accepted: aa.AcceptanceResult) -> None:
        text = accepted.public_record.read_text(encoding="utf-8")
        root = str(world["root"])
        assert root not in text and root.replace("\\", "/") not in text
        assert world["root"].name not in text
        for name in (fx.PDF_NAME, fx.DICTIONARY_NAME, at.ROW_MAP_FILE, atk.DETAILS_FILE,
                     rw.PLAN_FILE, ".pdf", ".json"):
            assert name not in text

    def test_the_public_record_carries_only_its_declared_keys(
            self, accepted: aa.AcceptanceResult) -> None:
        aa.check_public_shape(accepted.public)
        extra = copy.deepcopy(accepted.public)
        extra["derivative"]["quote"] = "anything"
        with pytest.raises(aa.AcceptanceRefused, match="quote"):
            aa.check_public_shape(extra)

    @pytest.mark.parametrize(("path", "value"), [
        (("policy", "policy_id"), {"quote": "anything"}),
        (("a6_structural_fidelity", "counts", "headings"), {"findings": "a heading's text"}),
        (("operator_signature", "attestations"), {"note": True}),
        (("not_evidence_of",), [{"quote": "anything"}]),
    ])
    def test_no_text_hides_inside_a_value_or_a_tally(
            self, accepted: aa.AcceptanceResult, path: tuple[str, ...], value: Any) -> None:
        changed = copy.deepcopy(accepted.public)
        target = changed
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        with pytest.raises(aa.AcceptanceRefused, match="closed set"):
            aa.check_public_shape(changed)

    def test_no_guess_and_no_passage_id_reaches_the_public_record(
            self, world: dict[str, Any], accepted: aa.AcceptanceResult) -> None:
        text = accepted.public_record.read_text(encoding="utf-8")
        assert "Helsinki" not in text
        for window in _read(world["attack_details"])["windows"]:
            for pid in window["passage_ids"]:
                assert f'"{pid}"' not in text

    @pytest.mark.parametrize(("field", "value"), [
        ("signed_by", "Orsolya Vantrell"),
        ("export_rule", {"rule_id": "exports approved by University of Kelpmoor",
                         "issued_by": "the data owner", "read_on": "2026-10-16"}),
    ])
    def test_an_operator_entry_naming_an_entity_is_refused(
            self, world: dict[str, Any], tmp_path: Path, field: str, value: Any) -> None:
        operator = _write_json(tmp_path / "input.json",
                               _operator_input(world["derivative_sha256"], **{field: value}))
        with pytest.raises(aa.AcceptanceRefused, match="entity dictionary"):
            _accept(world, tmp_path / "a7", operator_input=operator)
        assert not (tmp_path / "a7").exists()


# --------------------------------------------------------------------------- #
# Acceptance 2: the public record refuses unless A5 and A6 passed
# --------------------------------------------------------------------------- #


def _leak_fail(r: dict) -> None:
    r["reidentification"]["leak_scan"]["verdict"] = "fail"


def _leak_hit(r: dict) -> None:
    r["reidentification"]["leak_scan"]["counts"]["hits"] = {"person_name": 1}


def _attack_failed(r: dict) -> None:
    r["reidentification"]["model_attack"]["verdict"] = "failed"


def _attack_incomplete(r: dict) -> None:
    r["reidentification"]["model_attack"]["verdict"] = "incomplete"


def _attack_correct(r: dict) -> None:
    target = next(t for t in r["reidentification"]["model_attack"]["targets"]
                  if t["target"] == "partner")
    target["counts"]["correct"] = 1


def _attack_unlocated(r: dict) -> None:
    r["reidentification"]["model_attack"]["correct_unlocated"] = 1


def _fidelity_fail(r: dict) -> None:
    r["structural_fidelity"]["verdict"] = "fail"


def _fidelity_finding(r: dict) -> None:
    r["structural_fidelity"]["counts"]["figures"]["findings"] = 1


def _no_table(r: dict) -> None:
    r["table_1_4_1"]["synthetic"] = False


def _not_read(r: dict) -> None:
    r["operator"]["attestations"]["derivative_read"] = False


class TestPublicRecordRefuses:
    def test_the_accepted_private_record_builds(
            self, accepted: aa.AcceptanceResult, entities: matching.EntityDictionary) -> None:
        private = _read(accepted.private_record)
        assert aa.public_record(private, private_sha256=_sha(accepted.private_record),
                                entities=entities) == accepted.public

    @pytest.mark.parametrize(("change", "reason"), [
        (_leak_fail, "leak scan"),
        (_leak_hit, "leak scan"),
        (_attack_failed, "model attack"),
        (_attack_incomplete, "model attack"),
        (_attack_correct, "correct guess"),
        (_attack_unlocated, "correct guess"),
        (_fidelity_fail, "structural fidelity"),
        (_fidelity_finding, "finding"),
        (_no_table, "Table 1.4.1"),
        (_not_read, "derivative_read"),
    ])
    def test_it_refuses_unless_a5_and_a6_passed(
            self, accepted: aa.AcceptanceResult, entities: matching.EntityDictionary,
            change: Callable[[dict], None], reason: str) -> None:
        private = _read(accepted.private_record)
        change(private)
        with pytest.raises(aa.AcceptanceRefused, match=reason):
            aa.public_record(private, private_sha256="0" * 64, entities=entities)

    def test_a_failing_leak_scan_report_refuses_the_acceptance(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        def fail(r: dict) -> None:
            r["verdict"] = "fail"
            r["counts"]["hits"] = {"person_name": 1}
        report = _tampered(world, tmp_path, world["leak_scan"], fail)
        with pytest.raises(aa.AcceptanceRefused, match="leak scan"):
            _accept(world, tmp_path / "a7", leak_scan=report)
        assert not (tmp_path / "a7").exists()

    def test_a_fidelity_report_with_a_finding_refuses_the_acceptance(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        def finding(r: dict) -> None:
            r["verdict"] = "fail"
            r["counts"]["headings"]["findings"] = 1
        report = _tampered(world, tmp_path, world["fidelity"], finding)
        with pytest.raises(aa.AcceptanceRefused, match="structural fidelity"):
            _accept(world, tmp_path / "a7", structural_fidelity=report)


# --------------------------------------------------------------------------- #
# Every record must be of this derivative, this policy and this chain
# --------------------------------------------------------------------------- #


class TestBinding:
    @pytest.mark.parametrize("which", ["leak_scan", "attack", "fidelity"])
    def test_a_report_of_another_derivative_is_refused(
            self, world: dict[str, Any], tmp_path: Path, which: str) -> None:
        def other(r: dict) -> None:
            if which == "leak_scan":
                r["input"]["sha256"] = "f" * 64
            else:
                r["input"]["derivative_sha256"] = "f" * 64
        report = _tampered(world, tmp_path, world[which], other)
        key = {"leak_scan": "leak_scan", "attack": "reidentification_report",
               "fidelity": "structural_fidelity"}[which]
        with pytest.raises(aa.AcceptanceRefused, match="another derivative"):
            _accept(world, tmp_path / "a7", **{key: report})

    def test_a_report_under_another_policy_is_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        report = _tampered(world, tmp_path, world["leak_scan"],
                           lambda r: r.update(policy_sha256="e" * 64))
        with pytest.raises(aa.AcceptanceRefused, match="policy"):
            _accept(world, tmp_path / "a7", leak_scan=report)

    def test_a_stage_log_the_fidelity_report_did_not_bind_is_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        log = _tampered(world, tmp_path, world["stage_logs"][1], lambda r: r.update(extra=1))
        with pytest.raises(aa.AcceptanceRefused, match="stage log"):
            _accept(world, tmp_path / "a7", stage_logs=[world["stage_logs"][0], log])

    def test_a_row_map_of_another_table_is_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        row_map = _tampered(world, tmp_path, world["row_map"],
                            lambda r: r["output"].update(sha256="d" * 64))
        with pytest.raises(aa.AcceptanceRefused, match="row map"):
            _accept(world, tmp_path / "a7", table_row_map=row_map)

    def test_a_rewrite_plan_of_another_input_is_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        plan = _tampered(world, tmp_path, world["rewrite_plan"],
                         lambda r: r["input"].update(derivative_sha256="c" * 64))
        with pytest.raises(aa.AcceptanceRefused, match="rewrite plan"):
            _accept(world, tmp_path / "a7", rewrite_plan=plan)

    def test_a_rewrite_plan_by_another_model_than_the_attack_names_is_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        plan = _tampered(world, tmp_path, world["rewrite_plan"],
                         lambda r: r["model"].update(model_id="eu.anthropic.claude-other"))
        with pytest.raises(aa.AcceptanceRefused, match="A3 model"):
            _accept(world, tmp_path / "a7", rewrite_plan=plan)

    def test_a_rewrite_plan_with_unapplied_edits_is_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        def edits(r: dict) -> None:
            r["passages"][0]["edits"] = [{"start": 0, "end": 1}]
        plan = _tampered(world, tmp_path, world["rewrite_plan"], edits)
        with pytest.raises(aa.AcceptanceRefused, match="no stage applied"):
            _accept(world, tmp_path / "a7", rewrite_plan=plan)

    def test_a_rewrite_plan_with_queued_entities_is_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        plan = _tampered(world, tmp_path, world["rewrite_plan"],
                         lambda r: r["passages"][0].update(proposals=1))
        with pytest.raises(aa.AcceptanceRefused, match="proposed entit"):
            _accept(world, tmp_path / "a7", rewrite_plan=plan)

    def test_details_of_another_attack_are_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        details = _tampered(world, tmp_path, world["attack_details"],
                            lambda r: r.update(derivative_sha256="b" * 64))
        with pytest.raises(aa.AcceptanceRefused, match="details"):
            _accept(world, tmp_path / "a7", reidentification_details=details)

    def test_an_operator_input_for_another_derivative_is_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        operator = _write_json(tmp_path / "input.json", _operator_input("a" * 64))
        with pytest.raises(aa.AcceptanceRefused, match="another derivative"):
            _accept(world, tmp_path / "a7", operator_input=operator)

    @pytest.mark.parametrize(("changes", "reason"), [
        ({"decision": "reject"}, "decision"),
        ({"pipeline_revision": "HEAD"}, "pipeline_revision"),
        ({"signed_on": "16 October"}, "signed_on"),
        ({"signed_by": " "}, "signed_by"),
        ({"export_rule": None}, "export_rule"),
    ])
    def test_an_incomplete_operator_input_is_refused(
            self, world: dict[str, Any], tmp_path: Path, changes: dict, reason: str) -> None:
        operator = _write_json(tmp_path / "input.json",
                               _operator_input(world["derivative_sha256"], **changes))
        with pytest.raises(aa.AcceptanceRefused, match=reason):
            _accept(world, tmp_path / "a7", operator_input=operator)

    def test_a_dictionary_with_another_hash_is_refused(
            self, world: dict[str, Any], tmp_path: Path) -> None:
        with pytest.raises(aa.AcceptanceRefused, match="dictionary"):
            _accept(world, tmp_path / "a7", dictionary_sha256="a" * 64)

    def test_a_path_inside_the_repository_is_refused(self, world: dict[str, Any]) -> None:
        with pytest.raises(ai.IntakeRefused, match="inside this repository"):
            _accept(world, REPO / ".scratch" / "an11_out")
        assert not (REPO / ".scratch" / "an11_out").exists()


# --------------------------------------------------------------------------- #
# Acceptance 3: the written export procedure
# --------------------------------------------------------------------------- #

PROCEDURE = REPO / aa.EXPORT_PROCEDURE_REL


def _procedure_steps() -> list[dict[str, str]]:
    """The rows of the procedure's step table: | Step | Action | Rule that permits it |."""
    lines = PROCEDURE.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith("| Step | Action | Rule that permits it |"))
    rows: list[dict[str, str]] = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        assert len(cells) == 3, line
        rows.append({"step": cells[0], "action": cells[1], "rule": cells[2]})
    return rows


class TestExportProcedure:
    def test_every_step_names_an_action_and_the_rule_that_permits_it(self) -> None:
        steps = _procedure_steps()
        assert [s["step"] for s in steps] == [str(n) for n in range(1, len(steps) + 1)]
        assert len(steps) >= 6
        for step in steps:
            assert step["action"], step
            assert step["rule"], step

    def test_every_rule_cites_a_source_that_exists(self) -> None:
        cited = re.compile(r"`([^`]+\.(?:md|json|py))`")
        for step in _procedure_steps():
            files = cited.findall(step["rule"])
            assert files, f"step {step['step']} cites no source file"
            for rel in files:
                assert (REPO / rel).is_file(), f"step {step['step']}: {rel}"

    def test_the_procedure_exports_through_the_s3_gateway_under_decision_7(self) -> None:
        text = PROCEDURE.read_text(encoding="utf-8")
        assert "S3 gateway" in text
        assert "Decision 7" in text
        assert "ec2-ssm-role" in text
        rules = " ".join(s["rule"] for s in _procedure_steps())
        assert "ADR-001-security-decisions.md" in rules
        assert "msca_dn_pe09_runbook.md" in rules
        assert aa.J0_RECORD_REL.split("/")[-1] in rules

    def test_the_procedure_names_what_never_leaves(self) -> None:
        text = PROCEDURE.read_text(encoding="utf-8")
        for item in ("entity dictionary", "mapping table", "row map", "edit log",
                     "re-identification details", "private acceptance record"):
            assert item in text, item

    def test_the_procedure_declares_what_it_has_not_confirmed(self) -> None:
        text = PROCEDURE.read_text(encoding="utf-8")
        assert "Unresolved" in text
