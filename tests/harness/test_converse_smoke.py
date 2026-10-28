"""
The Converse blind pass on the private host (ticket AN12).

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN12:

3. A synthetic blind pass over Converse freezes on the host with a validated
   receipt.

The live pass is the operator's. These tests drive the same command over the
real :class:`~runner.transport.bedrock_converse.BedrockConverseBackend` with
only ``boto3.client`` replaced. ``prepare`` builds the synthetic world outside
the repository, runs the preflight and drafts a receipt with no assessor
call. ``assess`` refuses until the operator's receipt is green, as V13
requires before a private run, then assesses, freezes and reads the receipt
against the report.

No test here reaches a network.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from harness import execution_receipt as er
from harness.commands import converse_smoke as cs
from tests.harness.test_blind_leakage import FROZEN
from tests.harness.test_converse_judge import PIN, VERSION, client, converse_env  # noqa: F401


def _prepare(root: Path) -> int:
    return cs.main(["prepare", "--root", str(root), "--assessor-model", PIN,
                    "--assessor-version", VERSION], clock=lambda: FROZEN)


def _assess(root: Path, receipt: Path) -> int:
    return cs.main(["assess", "--root", str(root), "--receipt", str(receipt)],
                   clock=lambda: FROZEN)


def _fill(draft: Path, out: Path) -> Path:
    """What the operator writes: the parts the pass cannot measure."""
    doc = json.loads(draft.read_text(encoding="utf-8"))
    doc.update(authored_on="2026-10-16", review_state="operator_reviewed",
               declared_status="Confirmed", purpose="AN12 synthetic Converse smoke pass",
               written_by="the operator")
    if doc["repository_revision"].startswith("<"):
        # Here no bundle is installed, so the pass found no manifest to read it from.
        doc["repository_revision"] = "0123456789abcdef0123456789abcdef01234567"
    doc["processing_route"] = {
        "authority": "the private environment's rule for synthetic test data",
        "processing": "synthetic prompts only", "export": "nothing",
        "verified_on": "2026-10-16", "verified_by": "the operator",
    }
    doc["isolation_check"].update(
        evidence=["tests/harness/test_converse_judge.py::TestTheJudgeBuildsConverse",
                  "the rendered request inspected in the receipt draft"],
        verified_on="2026-10-16", verified_by="the operator")
    out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return out


@pytest.fixture
def prepared(converse_env, client, tmp_path) -> tuple[Path, Any]:
    root = tmp_path / "smoke"
    assert _prepare(root) == 0
    return root, client


@pytest.fixture
def assessed(prepared) -> tuple[Path, Any, Path]:
    root, client = prepared
    receipt = _fill(root / cs.DRAFT_FILE, root / "readiness_receipt.json")
    assert _assess(root, receipt) == 0
    return root, client, receipt


class TestPrepare:
    def test_it_makes_no_assessor_call(self, prepared):
        _root, client = prepared
        assert client.requests == []

    def test_the_draft_carries_the_request_the_builder_makes(self, prepared):
        root, _client = prepared
        draft = json.loads((root / cs.DRAFT_FILE).read_text(encoding="utf-8"))
        assert draft["transport"] == "bedrock-converse"
        assert draft["rendered_request"]["model_id"] == PIN
        assert draft["rendered_request"]["temperature"] == 0.0
        assert draft["rendered_request"]["tool_config_present"] is False
        assert draft["rendered_request"]["region"] == "eu-west-1"
        assert draft["model_identity"]["pin"] == f"{PIN}@{VERSION}"
        assert draft["private_clone_root"] == str(root / "world")
        assert Path(draft["preflight"]["report_path"]).is_file()
        assert not Path(draft["checkpoint"]["path"]).exists()

    def test_the_draft_leaves_the_operators_parts_unfilled(self, prepared):
        root, _client = prepared
        draft = json.loads((root / cs.DRAFT_FILE).read_text(encoding="utf-8"))
        for key in ("authored_on", "review_state", "declared_status", "purpose", "written_by"):
            assert draft[key].startswith("<"), key
        assert draft["processing_route"]["authority"].startswith("<")
        assert draft["isolation_check"]["verified_by"].startswith("<")


class TestAssess:
    def test_an_unfilled_draft_is_refused_before_any_call(self, prepared):
        root, client = prepared
        assert _assess(root, root / cs.DRAFT_FILE) == cs.EXIT_REFUSED
        assert client.requests == []

    def test_a_receipt_that_is_not_green_is_refused_before_any_call(self, prepared):
        root, client = prepared
        receipt = _fill(root / cs.DRAFT_FILE, root / "readiness_receipt.json")
        doc = json.loads(receipt.read_text(encoding="utf-8"))
        doc["checkpoint"]["already_exists"] = True
        receipt.write_text(json.dumps(doc), encoding="utf-8")
        assert _assess(root, receipt) == cs.EXIT_REFUSED
        assert client.requests == []

    def test_a_green_receipt_lets_the_pass_run_and_freeze(self, assessed):
        root, client, _receipt = assessed
        (report_path,) = (root / "world" / "reports").glob("*.json")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["assessor_transport"] == "bedrock-converse"
        assert report["scope"] == "complete"
        assert list((root / "baseline").glob("*.json")), "the pass did not freeze"
        assert client.requests and {r["modelId"] for r in client.requests} == {PIN}
        assert all("toolConfig" not in r for r in client.requests)

    def test_the_run_writes_the_checkpoint_the_receipt_names(self, assessed):
        root, _client, receipt = assessed
        named = json.loads(receipt.read_text(encoding="utf-8"))["checkpoint"]["path"]
        assert Path(named).is_file()

    def test_the_receipt_stays_green_against_the_report(self, assessed):
        root, _client, receipt = assessed
        result = cs.check_receipt(root, receipt)
        assert isinstance(result, er.ReceiptCheck) and result.green
        assert cs.main(["check", "--root", str(root), "--receipt", str(receipt)]) == 0

    def test_a_receipt_that_disagrees_with_the_report_is_reported(self, assessed):
        root, _client, receipt = assessed
        doc = json.loads(receipt.read_text(encoding="utf-8"))
        doc["rendered_request"]["max_tokens"] += 1
        for setting in doc["effective_settings"]:
            if setting["name"] == "max_tokens":
                setting["value"] = str(doc["rendered_request"]["max_tokens"])
        receipt.write_text(json.dumps(doc), encoding="utf-8")
        assert cs.main(["check", "--root", str(root), "--receipt", str(receipt)]) \
            == cs.EXIT_FINDINGS

    def test_a_second_pass_on_the_same_root_is_refused(self, assessed):
        root, client, receipt = assessed
        sent = len(client.requests)
        assert _assess(root, receipt) == cs.EXIT_REFUSED
        assert len(client.requests) == sent


class TestRefusals:
    def test_a_root_inside_the_repository_is_refused(self, converse_env, client):
        root = cs.THIS_REPOSITORY / "converse_smoke_here"
        assert _prepare(root) == cs.EXIT_REFUSED
        assert not root.exists()

    def test_a_region_outside_adr_001_is_refused(self, converse_env, client, tmp_path,
                                                 monkeypatch):
        monkeypatch.setenv("AWS_REGION", "eu-central-1")
        assert _prepare(tmp_path / "smoke") == cs.EXIT_REFUSED
        assert not (tmp_path / "smoke" / "world").exists()

    def test_aws_default_region_alone_is_refused(self, converse_env, client, tmp_path,
                                                 monkeypatch):
        # R9e point 9 (F-R9-7): only AWS_REGION counts, as in production mode.
        monkeypatch.delenv("AWS_REGION", raising=False)
        monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")
        assert _prepare(tmp_path / "smoke") == cs.EXIT_REFUSED
        assert not (tmp_path / "smoke" / "world").exists()
        with pytest.raises(cs.SmokeRefused, match="AWS_DEFAULT_REGION alone"):
            cs._region()

    def test_the_hosts_region_is_accepted(self, monkeypatch):
        from runner.transport.config import BEDROCK_CONVERSE_EU

        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
        monkeypatch.setenv("AWS_REGION", BEDROCK_CONVERSE_EU.default_region)
        assert cs._region() == BEDROCK_CONVERSE_EU.default_region

    def test_an_existing_world_is_refused(self, converse_env, client, tmp_path):
        root = tmp_path / "smoke"
        (root / "world").mkdir(parents=True)
        assert _prepare(root) == cs.EXIT_REFUSED
