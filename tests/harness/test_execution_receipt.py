"""The private execution readiness receipt and its validator (ticket V13).

The receipt is the operator's pre-run evidence about the assessor: which CLI,
which version, which settings actually reach it, which directory the child runs
in, and which preflight the run is bound to. It is produced in the private
environment and never enters this repository, so the only thing testable here
is the validator — and the only way to test a validator is to make every one of
its refusals fire.

So every case below builds a synthetic receipt in ``tmp_path``. A validator
exercised on a complete receipt alone is a validator whose refusals have never
run. Two more cases guard the boundary the ticket's fifth criterion sets: the
committed template is refused, and a receipt inside this repository is refused.

The receipts below name no instrument. The intended Stage A pair is passed in,
which is the validator's own contract.

Offline. Nothing here invokes an assessor, a CLI or Claude.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from harness import execution_receipt as er
from harness import historical_profile as hp
from harness.blind_assessment import BLIND_REPORT_RECORD_TYPE
from harness.blind_baseline import BASELINE_CHECKS, TRANSPORT_ISOLATION_EVIDENCE
from harness.commands import execution_receipt as command
from harness.record_binding import REVIEW_STATES, STATUSES
from runner.paths import find_repo_root

REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)

CLONE = "/private/clone"
WORKDIR = "/private/scratch/blind_assessor_7f1c"
PREFLIGHT_REL = "reports/preflight_0001.json"
MANIFEST = "/private/clone/docs/tier4_orchestration_state/dev_graph/imports/original.json"
MANIFEST_SHA = "a" * 64
CANDIDATE = "official_original"
PROFILE_ID = "a_historical_profile"
PROFILE_PATH = "harness/profiles/historical.json"
PROFILE_SHA = "b" * 64
PROFILE_VERSION = "c" * 40
PACK_SET = "d" * 64
SCOPE = "content_focused"


# --------------------------------------------------------------------------- #
# Synthetic world
# --------------------------------------------------------------------------- #


def _preflight_doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "record_type": "evidence_preflight_report",
        "document_id": CANDIDATE,
        "profile_id": PROFILE_ID,
        "profile_version": PROFILE_VERSION,
        "pack_set_hash": PACK_SET,
        "grounding_scope": {"declared": SCOPE},
        "import_manifest": {"path": MANIFEST, "sha256": MANIFEST_SHA},
        "packs": [{"expectation_key": "k", "status": "complete"}],
        "criterion_inputs": [{"criterion_id": "c", "complete": True}],
    }
    doc.update(overrides)
    return doc


def _argv() -> list[str]:
    return [
        "/usr/local/bin/claude",
        "-p",
        "--model",
        "claude-opus-4-8",
        "--output-format",
        "stream-json",
        "--verbose",
        "--tools",
        "",
        "--strict-mcp-config",
        "--system-prompt",
        "<the rubric system prompt>",
    ]


def _receipt_doc(transport: str = "claude-cli", **overrides: Any) -> dict[str, Any]:
    """A complete receipt. Every case below removes or alters one thing."""
    if transport == CONVERSE:
        doc = _converse_receipt_doc()
        doc.update(overrides)
        return doc
    doc: dict[str, Any] = {
        "schema": er.SCHEMA,
        "record_type": er.RECEIPT_RECORD_TYPE,
        "receipt_id": "synthetic_readiness_receipt",
        "authored_on": "2026-10-13",
        "review_state": "operator_reviewed",
        "declared_status": "Confirmed",
        "purpose": "exercise the validator",
        "written_by": "tests",
        "transport": transport,
        "private_clone_root": CLONE,
        "repository_revision": "ddd20bf",
        "processing_route": {
            "authority": "the private environment's own processing rule, section 4",
            "processing": "assessor prompts over the imported original may be sent",
            "export": "hashes, counts and dates leave; no passage and no score",
            "verified_on": "2026-10-13",
            "verified_by": "the private operator",
        },
        "cli_version": {
            "executable": "/usr/local/bin/claude",
            "version_output": "2.0.31 (Claude Code)",
            "obtained_by": "/usr/local/bin/claude --version",
            "verified_on": "2026-10-13",
        },
        "model_identity": {
            "pin": "claude-opus-4-8@claude-cli@2026-10-13",
            "attested": False,
            "note": "a declared identifier; the provider attests nothing on this transport",
        },
        "effective_settings": [
            {
                "name": "model",
                "value": "claude-opus-4-8",
                "transmitted": True,
                "transport_evidence": "rendered as --model",
            },
            {
                "name": "tools",
                "value": "",
                "transmitted": True,
                "transport_evidence": 'rendered as --tools ""',
            },
            {
                "name": "strict_mcp_config",
                "value": "true",
                "transmitted": True,
                "transport_evidence": "rendered as --strict-mcp-config",
            },
            {
                "name": "working_directory",
                "value": WORKDIR,
                "transmitted": True,
                "transport_evidence": "the child's cwd",
            },
            {
                "name": "temperature",
                "value": "0",
                "transmitted": False,
                "transport_evidence": "the CLI takes no temperature argument",
            },
            {
                "name": "max_tokens",
                "value": "32000",
                "transmitted": False,
                "transport_evidence": "the ceiling is the transport's own env var",
            },
        ],
        "rendered_invocation": {
            "argv": _argv(),
            "rendered_by": "runner/claude_transport.py",
            "working_directory": WORKDIR,
        },
        "isolation_check": {
            "working_directory": WORKDIR,
            "working_directory_outside_every_clone": True,
            "operating_system_sandbox": False,
            "evidence": [
                "tests/harness/test_subscription_judge.py::TestBlindnessAtTheArgvLevel",
                "tests/harness/test_blind_leakage.py",
            ],
            "verified_on": "2026-10-13",
            "verified_by": "the private operator",
        },
        "checkpoint": {
            "path": "/private/clone/.harness/checkpoints/checkpoint_0ab1c2d3e4f5_0001.jsonl",
            "already_exists": False,
        },
        "preflight": {
            "report_path": PREFLIGHT_REL,
            "report_sha256": "",
            "pack_set_hash": PACK_SET,
            "document_id": CANDIDATE,
            "profile_id": PROFILE_ID,
            "profile_path": PROFILE_PATH,
            "profile_sha256": PROFILE_SHA,
            "profile_version": PROFILE_VERSION,
            "import_manifest_path": MANIFEST,
            "import_manifest_sha256": MANIFEST_SHA,
            "grounding_scope": SCOPE,
        },
    }
    doc.update(overrides)
    return doc


CONVERSE = "bedrock-converse"
CONVERSE_MODEL = "eu.anthropic.claude-sonnet-4-6"

TEMPLATES = (
    "execution_receipt_template.json",
    "execution_receipt_template_bedrock_converse.json",
)


def _converse_receipt_doc() -> dict[str, Any]:
    """A complete receipt for a Converse run: no CLI, no argv, no directory.

    Built from the CLI receipt so the shared sections stay the same, with the
    CLI's two sections replaced by the request Converse sends.
    """
    doc = _receipt_doc()
    del doc["cli_version"], doc["rendered_invocation"]
    doc["transport"] = CONVERSE
    doc["model_identity"]["pin"] = f"{CONVERSE_MODEL}@{CONVERSE}-eu-west-1@2026-10-14"
    doc["effective_settings"] = [
        {
            "name": "model",
            "value": CONVERSE_MODEL,
            "transmitted": True,
            "transport_evidence": "sent as modelId",
        },
        {
            "name": "temperature",
            "value": "0",
            "transmitted": True,
            "transport_evidence": "sent as inferenceConfig.temperature",
        },
        {
            "name": "max_tokens",
            "value": "4096",
            "transmitted": True,
            "transport_evidence": "sent as inferenceConfig.maxTokens",
        },
    ]
    doc["rendered_request"] = {
        "model_id": CONVERSE_MODEL,
        "temperature": 0.0,
        "max_tokens": 4096,
        "tool_config_present": False,
        "region": "eu-west-1",
        "rendered_by": "runner/transport/bedrock_converse.py",
    }
    doc["isolation_check"] = {
        "tool_config_sent": False,
        "child_process": False,
        "evidence": [
            "tests/harness/test_converse_judge.py::TestTheJudgeBuildsConverse",
            "the rendered request inspected: no toolConfig key",
        ],
        "verified_on": "2026-10-14",
        "verified_by": "the private operator",
    }
    return doc


#: Every field of every object-shaped section, and every top-level field, read
#: off the complete receipt above. Generated rather than hand-listed: the
#: ticket asks for refusal on each missing field, and a hand-list goes stale
#: the moment the schema grows one.
_SECTION_FIELDS: list[tuple[str, str]] = [
    (section, field)
    for section, body in _receipt_doc().items()
    if isinstance(body, dict)
    for field in body
]
_FIELD_IDS: list[str] = [f"{section}.{field}" for section, field in _SECTION_FIELDS]

#: The same, for the two sections a Converse receipt fills differently.
_CONVERSE_SECTION_FIELDS: list[tuple[str, str]] = [
    (section, field)
    for section, body in _converse_receipt_doc().items()
    if section in ("rendered_request", "isolation_check")
    for field in body
]

#: The top-level fields, minus the two the reader checks by other rules: the
#: schema has its own refusal, and record_type is not read.
_TOP_LEVEL_FIELDS: list[str] = [
    field
    for field, body in _receipt_doc().items()
    if not isinstance(body, (dict, list)) and field not in ("schema", "record_type")
]


def _world(
    tmp_path: Path,
    *,
    receipt: dict[str, Any] | None = None,
    preflight: dict[str, Any] | None = None,
) -> Path:
    """Write a receipt and the preflight report it names. Returns the receipt."""
    doc = _receipt_doc() if receipt is None else receipt
    report = _preflight_doc() if preflight is None else preflight

    report_path = tmp_path / PREFLIGHT_REL
    report_path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(report, indent=2, sort_keys=True)
    report_path.write_text(body, encoding="utf-8")

    block = doc.get("preflight")
    if isinstance(block, dict) and block.get("report_sha256") == "":
        block["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()

    path = tmp_path / "readiness_receipt.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


def _intended(**overrides: Any) -> er.IntendedPair:
    kwargs: dict[str, Any] = {
        "candidate_document_id": CANDIDATE,
        "profile_id": PROFILE_ID,
        "profile_path": PROFILE_PATH,
        "profile_sha256": PROFILE_SHA,
    }
    kwargs.update(overrides)
    return er.IntendedPair(**kwargs)


def _check(tmp_path: Path, **kwargs: Any) -> er.ReceiptCheck:
    path = _world(tmp_path, **kwargs)
    receipt = er.load_receipt(path)
    return er.check(receipt, _intended(), receipt_dir=path.parent)


# --------------------------------------------------------------------------- #
# The complete receipt
# --------------------------------------------------------------------------- #


class TestACompleteReceipt:
    def test_it_validates(self, tmp_path: Path) -> None:
        """Non-vacuity: every refusal below is a refusal of something this
        receipt does not do."""
        report = _check(tmp_path)
        assert report.green, report.lines()
        assert report.findings_total == 0

    def test_the_loader_reads_every_section(self, tmp_path: Path) -> None:
        receipt = er.load_receipt(_world(tmp_path))
        assert receipt.transport == "claude-cli"
        assert receipt.isolation.operating_system_sandbox is False
        assert len(receipt.settings) == len(er.TRANSPORT_SETTINGS["claude-cli"])
        assert receipt.preflight.document_id == CANDIDATE
        assert receipt.source.endswith("readiness_receipt.json")


# --------------------------------------------------------------------------- #
# What the loader refuses to read at all
# --------------------------------------------------------------------------- #


class TestTheLoaderRefusesAnIncompleteReceipt:
    @pytest.mark.parametrize("section", er.REQUIRED_SECTIONS["claude-cli"])
    def test_a_missing_section_is_refused(self, tmp_path: Path, section: str) -> None:
        doc = _receipt_doc()
        del doc[section]
        path = _world(tmp_path, receipt=doc)
        with pytest.raises(er.ReceiptError, match=section):
            er.load_receipt(path)

    @pytest.mark.parametrize(("section", "field"), _SECTION_FIELDS, ids=_FIELD_IDS)
    def test_a_missing_field_is_refused(
        self, tmp_path: Path, section: str, field: str
    ) -> None:
        """Every field of every object section, generated from the receipt
        rather than hand-listed, so a field added to the schema and not to the
        reader fails here."""
        doc = _receipt_doc()
        del doc[section][field]
        path = _world(tmp_path, receipt=doc)
        with pytest.raises(er.ReceiptError, match=field):
            er.load_receipt(path)

    @pytest.mark.parametrize("field", _TOP_LEVEL_FIELDS)
    def test_a_missing_top_level_field_is_refused(
        self, tmp_path: Path, field: str
    ) -> None:
        doc = _receipt_doc()
        del doc[field]
        path = _world(tmp_path, receipt=doc)
        with pytest.raises(er.ReceiptError, match=field):
            er.load_receipt(path)

    @pytest.mark.parametrize("field", ["name", "value", "transmitted", "transport_evidence"])
    def test_a_setting_missing_a_field_is_refused(
        self, tmp_path: Path, field: str
    ) -> None:
        doc = _receipt_doc()
        del doc["effective_settings"][0][field]
        path = _world(tmp_path, receipt=doc)
        with pytest.raises(er.ReceiptError, match=field):
            er.load_receipt(path)

    def test_an_empty_string_is_as_absent_as_a_missing_one(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        doc["cli_version"]["version_output"] = "   "
        path = _world(tmp_path, receipt=doc)
        with pytest.raises(er.ReceiptError, match="version_output"):
            er.load_receipt(path)

    def test_a_placeholder_is_not_evidence(self, tmp_path: Path) -> None:
        """The template's own form. A receipt carrying it is a template."""
        doc = _receipt_doc()
        doc["cli_version"]["version_output"] = "<what claude --version printed>"
        path = _world(tmp_path, receipt=doc)
        with pytest.raises(er.ReceiptError, match="placeholder"):
            er.load_receipt(path)

    def test_the_rendered_system_prompt_may_carry_angle_brackets(
        self, tmp_path: Path
    ) -> None:
        """The placeholder rule reads declared evidence, not the argv the
        transport rendered, which carries whatever the prompt carries."""
        report = _check(tmp_path)
        assert report.green, report.lines()

    def test_a_wrong_schema_is_refused(self, tmp_path: Path) -> None:
        path = _world(tmp_path, receipt=_receipt_doc(schema="something/else"))
        with pytest.raises(er.ReceiptError, match="schema"):
            er.load_receipt(path)

    def test_an_unknown_transport_is_refused(self, tmp_path: Path) -> None:
        """The validator cannot say which settings reach a transport it has no
        table for, so it does not guess."""
        path = _world(tmp_path, receipt=_receipt_doc(transport="some-other-transport"))
        with pytest.raises(er.ReceiptError, match="transport"):
            er.load_receipt(path)

    def test_a_file_that_is_not_json_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "r.json"
        path.write_text("not json", encoding="utf-8")
        with pytest.raises(er.ReceiptError, match="JSON"):
            er.load_receipt(path)

    def test_an_absent_file_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(er.ReceiptError):
            er.load_receipt(tmp_path / "absent.json")


# --------------------------------------------------------------------------- #
# The intended Stage A pair
# --------------------------------------------------------------------------- #


class TestTheBindings:
    def test_another_candidate_is_refused(self, tmp_path: Path) -> None:
        path = _world(tmp_path)
        receipt = er.load_receipt(path)
        report = er.check(
            receipt,
            _intended(candidate_document_id="a_different_document"),
            receipt_dir=path.parent,
        )
        assert report.candidate_binding_mismatch
        assert not report.green

    def test_another_profile_is_refused(self, tmp_path: Path) -> None:
        path = _world(tmp_path)
        receipt = er.load_receipt(path)
        report = er.check(
            receipt,
            _intended(profile_sha256="e" * 64),
            receipt_dir=path.parent,
        )
        assert report.profile_binding_mismatch
        assert not report.green

    def test_another_profile_id_is_refused(self, tmp_path: Path) -> None:
        path = _world(tmp_path)
        receipt = er.load_receipt(path)
        report = er.check(
            receipt,
            _intended(profile_id="a_different_profile"),
            receipt_dir=path.parent,
        )
        assert report.profile_binding_mismatch


# --------------------------------------------------------------------------- #
# Criterion 3 — a setting is transmitted only where the transport sends it
# --------------------------------------------------------------------------- #


class TestWhatTheTransportActuallySends:
    def test_the_table_covers_every_transport_that_declares_isolation(self) -> None:
        """Single-sourced against the freeze's own isolation table: a
        transport that owes isolation evidence is exactly the transport a
        receipt describes. Only the one with a child process has an argv."""
        declares = {
            name for name, evidence in TRANSPORT_ISOLATION_EVIDENCE.items() if evidence
        }
        assert set(er.TRANSPORT_SETTINGS) == declares
        assert set(er.REQUIRED_SECTIONS) == declares
        runs_a_child = {
            name
            for name, evidence in TRANSPORT_ISOLATION_EVIDENCE.items()
            if evidence and evidence.get("child_process", True)
        }
        assert set(er.ARGV_BLINDNESS_CONTROLS) == runs_a_child == {"claude-cli"}

    def test_a_temperature_claimed_transmitted_is_refused(self, tmp_path: Path) -> None:
        """The pinned temperature reaches no provider on this transport: the
        CLI takes no temperature argument."""
        doc = _receipt_doc()
        for setting in doc["effective_settings"]:
            if setting["name"] == "temperature":
                setting["transmitted"] = True
        report = _check(tmp_path, receipt=doc)
        assert report.settings_claimed_transmitted_the_transport_does_not_send
        assert not report.green

    def test_a_token_limit_claimed_transmitted_is_refused(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        for setting in doc["effective_settings"]:
            if setting["name"] == "max_tokens":
                setting["transmitted"] = True
        report = _check(tmp_path, receipt=doc)
        assert report.settings_claimed_transmitted_the_transport_does_not_send

    def test_a_transmitted_setting_recorded_as_withheld_is_refused(
        self, tmp_path: Path
    ) -> None:
        """The other direction. A receipt understating what leaves is as wrong
        as one overstating it."""
        doc = _receipt_doc()
        for setting in doc["effective_settings"]:
            if setting["name"] == "model":
                setting["transmitted"] = False
        report = _check(tmp_path, receipt=doc)
        assert report.settings_recorded_as_withheld_the_transport_does_send

    def test_a_setting_the_receipt_omits_is_refused(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        doc["effective_settings"] = [
            s for s in doc["effective_settings"] if s["name"] != "temperature"
        ]
        report = _check(tmp_path, receipt=doc)
        assert report.settings_the_receipt_does_not_cover == ("temperature",)

    def test_a_setting_with_no_transport_evidence_is_refused(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        doc["effective_settings"][0]["transport_evidence"] = ""
        path = _world(tmp_path, receipt=doc)
        with pytest.raises(er.ReceiptError, match="transport_evidence"):
            er.load_receipt(path)


# --------------------------------------------------------------------------- #
# Criterion 3 — a directory is not a sandbox
# --------------------------------------------------------------------------- #


class TestIsolationIsNotASandbox:
    def test_a_claimed_sandbox_is_refused(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        doc["isolation_check"]["operating_system_sandbox"] = True
        report = _check(tmp_path, receipt=doc)
        assert report.isolation_claims_a_sandbox
        assert not report.green

    def test_a_working_directory_inside_the_clone_is_refused(self, tmp_path: Path) -> None:
        inside = f"{CLONE}/.harness/scratch"
        doc = _receipt_doc()
        doc["isolation_check"]["working_directory"] = inside
        doc["rendered_invocation"]["working_directory"] = inside
        report = _check(tmp_path, receipt=doc)
        assert report.isolation_working_directory_inside_the_clone

    def test_a_windows_working_directory_is_measured_too(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        doc["private_clone_root"] = "C:\\Private\\clone"
        doc["isolation_check"]["working_directory"] = "C:\\private\\Clone\\scratch"
        doc["rendered_invocation"]["working_directory"] = "C:\\private\\Clone\\scratch"
        doc["checkpoint"]["path"] = "C:\\Private\\clone\\.harness\\checkpoints\\c_0001.jsonl"
        report = _check(tmp_path, receipt=doc)
        assert report.isolation_working_directory_inside_the_clone

    def test_an_unclaimed_external_directory_is_refused(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        doc["isolation_check"]["working_directory_outside_every_clone"] = False
        report = _check(tmp_path, receipt=doc)
        assert report.isolation_not_outside_every_clone

    def test_the_two_working_directories_must_agree(self, tmp_path: Path) -> None:
        """The isolation check verifies a directory. The invocation runs in
        one. A receipt whose two differ verified something else."""
        doc = _receipt_doc()
        doc["rendered_invocation"]["working_directory"] = "/private/scratch/other"
        report = _check(tmp_path, receipt=doc)
        assert report.invocation_working_directory_disagrees


# --------------------------------------------------------------------------- #
# Criterion 4 — the isolation receipt is not the freeze record
# --------------------------------------------------------------------------- #


class TestItIsNotTheFreezesCheck:
    @pytest.mark.parametrize("condition", ["invocation_evidence", "preflight_binding"])
    def test_a_freeze_condition_cited_as_isolation_evidence_is_refused(
        self, tmp_path: Path, condition: str
    ) -> None:
        assert condition in BASELINE_CHECKS
        doc = _receipt_doc()
        doc["isolation_check"]["evidence"] = [f"the freeze's {condition} condition"]
        report = _check(tmp_path, receipt=doc)
        assert report.isolation_evidence_citing_the_freeze
        assert condition in report.isolation_evidence_citing_the_freeze[0]

    def test_a_freeze_record_cited_as_isolation_evidence_is_refused(
        self, tmp_path: Path
    ) -> None:
        doc = _receipt_doc()
        doc["isolation_check"]["evidence"] = [
            "/private/baselines/blind_baseline_0ab1c2d3e4f5.freeze.json"
        ]
        report = _check(tmp_path, receipt=doc)
        assert report.isolation_evidence_citing_the_freeze

    def test_the_freeze_is_reported_even_when_no_condition_is_named(
        self, tmp_path: Path
    ) -> None:
        """The defect is citing the freeze, so naming no condition does not
        make the citation sound."""
        doc = _receipt_doc()
        doc["isolation_check"]["evidence"] = ["the freeze passed, so the run was blind"]
        report = _check(tmp_path, receipt=doc)
        assert report.isolation_evidence_citing_the_freeze

    def test_a_condition_name_outside_a_freeze_citation_is_not_a_finding(
        self, tmp_path: Path
    ) -> None:
        """``assessor_transport`` is a freeze condition and an ordinary word.
        Evidence using it without citing the freeze is evidence."""
        assert "assessor_transport" in BASELINE_CHECKS
        doc = _receipt_doc()
        doc["isolation_check"]["evidence"] = [
            "read the rendered argv for the assessor_transport the report will record"
        ]
        report = _check(tmp_path, receipt=doc)
        assert report.green, report.lines()


# --------------------------------------------------------------------------- #
# The rendered invocation
# --------------------------------------------------------------------------- #


class TestTheRenderedInvocation:
    def test_a_missing_empty_tool_list_is_refused(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        argv = _argv()
        at = argv.index("--tools")
        del argv[at : at + 2]
        doc["rendered_invocation"]["argv"] = argv
        report = _check(tmp_path, receipt=doc)
        assert report.invocation_missing_a_blindness_control

    def test_a_non_empty_tool_list_is_refused(self, tmp_path: Path) -> None:
        """``--tools Read`` is an assessor that can open the repository."""
        doc = _receipt_doc()
        argv = _argv()
        argv[argv.index("--tools") + 1] = "Read,Glob"
        doc["rendered_invocation"]["argv"] = argv
        report = _check(tmp_path, receipt=doc)
        assert report.invocation_missing_a_blindness_control

    def test_a_missing_strict_mcp_config_is_refused(self, tmp_path: Path) -> None:
        """Measured 2026-10-05: an empty tool list alone still exposes the
        operator's MCP servers."""
        doc = _receipt_doc()
        doc["rendered_invocation"]["argv"] = [
            a for a in _argv() if a != "--strict-mcp-config"
        ]
        report = _check(tmp_path, receipt=doc)
        assert report.invocation_missing_a_blindness_control

    def test_an_empty_argv_is_refused_by_the_loader(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        doc["rendered_invocation"]["argv"] = []
        path = _world(tmp_path, receipt=doc)
        with pytest.raises(er.ReceiptError, match="argv"):
            er.load_receipt(path)


# --------------------------------------------------------------------------- #
# The CLI version and the model pin
# --------------------------------------------------------------------------- #


class TestTheVerifiedCliAndTheDeclaredModel:
    def test_a_version_not_read_from_the_cli_is_refused(self, tmp_path: Path) -> None:
        """The ticket's point: a version string is runtime evidence only when
        the CLI printed it."""
        doc = _receipt_doc()
        doc["cli_version"]["obtained_by"] = "the version in the environment's notes"
        report = _check(tmp_path, receipt=doc)
        assert report.cli_version_not_obtained_from_the_cli

    def test_a_pin_claimed_attested_is_refused(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        doc["model_identity"]["attested"] = True
        report = _check(tmp_path, receipt=doc)
        assert report.model_pin_claimed_attested

    def test_a_pin_that_does_not_name_the_transport_is_refused(
        self, tmp_path: Path
    ) -> None:
        doc = _receipt_doc()
        doc["model_identity"]["pin"] = "claude-opus-4-8@some-other-route@2026-10-13"
        report = _check(tmp_path, receipt=doc)
        assert report.model_pin_does_not_name_the_transport


# --------------------------------------------------------------------------- #
# The checkpoint
# --------------------------------------------------------------------------- #


class TestTheCheckpoint:
    def test_a_checkpoint_outside_the_clone_is_refused(self, tmp_path: Path) -> None:
        """The run writes it under the repository root, never under the output
        directory, so a path elsewhere is not the path the run will use."""
        doc = _receipt_doc()
        doc["checkpoint"]["path"] = "/private/reports/checkpoint_0001.jsonl"
        report = _check(tmp_path, receipt=doc)
        assert report.checkpoint_outside_the_clone

    def test_an_existing_checkpoint_is_refused(self, tmp_path: Path) -> None:
        """An existing file is never appended to, so a run pointed at one
        fails after the quota is spent rather than before."""
        doc = _receipt_doc()
        doc["checkpoint"]["already_exists"] = True
        report = _check(tmp_path, receipt=doc)
        assert report.checkpoint_already_exists


# --------------------------------------------------------------------------- #
# The preflight the receipt is bound to
# --------------------------------------------------------------------------- #


class TestThePreflightIsRead:
    def test_an_absent_preflight_is_a_finding(self, tmp_path: Path) -> None:
        path = _world(tmp_path)
        (tmp_path / PREFLIGHT_REL).unlink()
        receipt = er.load_receipt(path)
        report = er.check(receipt, _intended(), receipt_dir=path.parent)
        assert report.preflight_unreadable

    def test_a_moved_preflight_is_a_finding(self, tmp_path: Path) -> None:
        """The receipt pins the report's bytes. Different bytes are a
        different preflight."""
        path = _world(tmp_path)
        (tmp_path / PREFLIGHT_REL).write_text(
            json.dumps(_preflight_doc(), indent=4), encoding="utf-8"
        )
        receipt = er.load_receipt(path)
        report = er.check(receipt, _intended(), receipt_dir=path.parent)
        assert report.preflight_disagrees_with_the_receipt

    @pytest.mark.parametrize(
        "field", ["document_id", "profile_id", "profile_version", "pack_set_hash"]
    )
    def test_a_preflight_disagreeing_with_the_receipt_is_a_finding(
        self, tmp_path: Path, field: str
    ) -> None:
        report = _check(tmp_path, preflight=_preflight_doc(**{field: "something else"}))
        assert report.preflight_disagrees_with_the_receipt

    def test_a_preflight_naming_another_manifest_is_a_finding(self, tmp_path: Path) -> None:
        report = _check(
            tmp_path,
            preflight=_preflight_doc(
                import_manifest={"path": "/private/other.json", "sha256": MANIFEST_SHA}
            ),
        )
        assert report.preflight_disagrees_with_the_receipt

    def test_a_preflight_naming_no_manifest_is_incomplete(self, tmp_path: Path) -> None:
        """The runbook's rule: the manifest is named explicitly, and the
        resolver's predecessor default is never relied on."""
        report = _check(tmp_path, preflight=_preflight_doc(import_manifest=None))
        assert report.preflight_incomplete

    def test_a_preflight_declaring_no_grounding_scope_is_incomplete(
        self, tmp_path: Path
    ) -> None:
        report = _check(tmp_path, preflight=_preflight_doc(grounding_scope=None))
        assert report.preflight_incomplete

    def test_the_scope_is_read_where_the_preflight_writes_it(self, tmp_path: Path) -> None:
        """A preflight writes its declaration as ``grounding_scope.declared``.
        A block carrying only a ``scope`` key declares nothing (AN1b found the
        reader looking for that key, which no preflight writes)."""
        report = _check(tmp_path, preflight=_preflight_doc(grounding_scope={"scope": SCOPE}))
        assert report.preflight_incomplete

    @pytest.mark.parametrize("key", ["packs", "criterion_inputs"])
    def test_a_preflight_that_selected_nothing_is_incomplete(
        self, tmp_path: Path, key: str
    ) -> None:
        """Identifiers that line up are not completeness. A report with no
        realised pack binds a run that would read no evidence."""
        report = _check(tmp_path, preflight=_preflight_doc(**{key: []}))
        assert report.preflight_incomplete

    def test_an_insufficient_context_pack_is_not_incompleteness(
        self, tmp_path: Path
    ) -> None:
        """The pack set records it as an explicit outcome, so refusing it here
        would refuse a declared result."""
        report = _check(
            tmp_path,
            preflight=_preflight_doc(
                packs=[{"expectation_key": "k", "status": "insufficient_context"}]
            ),
        )
        assert report.green, report.lines()

    def test_a_record_of_another_type_is_incomplete(self, tmp_path: Path) -> None:
        report = _check(tmp_path, preflight=_preflight_doc(record_type="something_else"))
        assert report.preflight_incomplete

    def test_a_scope_the_receipt_does_not_declare_is_a_finding(self, tmp_path: Path) -> None:
        report = _check(
            tmp_path, preflight=_preflight_doc(grounding_scope={"declared": "source_grounded"})
        )
        assert report.preflight_disagrees_with_the_receipt


# --------------------------------------------------------------------------- #
# Criterion 5 — no private content enters this repository
# --------------------------------------------------------------------------- #


class TestTheReceiptStaysOutside:
    def test_a_receipt_inside_the_repository_is_refused(self, tmp_path: Path) -> None:
        """Measured against the repository root, the way the subscription
        judge measures its working directory."""
        inside = REPO_ROOT / "harness" / "execution_receipt_template.json"
        with pytest.raises(er.ReceiptError, match="outside"):
            er.receipt_path_outside(inside, REPO_ROOT)

    def test_a_receipt_outside_the_repository_is_accepted(self, tmp_path: Path) -> None:
        assert er.receipt_path_outside(tmp_path / "r.json", REPO_ROOT) == tmp_path / "r.json"

    @pytest.mark.parametrize("name", TEMPLATES)
    def test_the_committed_template_is_not_a_receipt(self, name: str) -> None:
        """Two independent protections, and this asserts the second: even
        copied out of the tree, the template's placeholders are not
        evidence."""
        template = REPO_ROOT / "harness" / name
        assert template.is_file(), "the operator has no template to fill in"
        with pytest.raises(er.ReceiptError, match="placeholder"):
            er.load_receipt(template)

    @pytest.mark.parametrize("name", TEMPLATES)
    def test_the_template_does_not_pre_answer_the_declarations(self, name: str) -> None:
        """An operator who fills only the angle brackets must not ship an
        unreviewed Confirmed. Both declarations are the operator's, so the
        template leaves both unfilled."""
        doc = json.loads((REPO_ROOT / "harness" / name).read_text(encoding="utf-8-sig"))
        assert doc["review_state"] not in REVIEW_STATES
        assert doc["declared_status"] not in STATUSES

    @pytest.mark.parametrize("name", TEMPLATES)
    def test_the_template_carries_every_required_section(self, name: str) -> None:
        doc = json.loads((REPO_ROOT / "harness" / name).read_text(encoding="utf-8-sig"))
        assert doc["schema"] == er.SCHEMA
        assert set(doc) - {"_what_this_is"} == set(_receipt_doc(doc["transport"]))
        for section in er.REQUIRED_SECTIONS[doc["transport"]]:
            assert section in doc, section
        for section, body in _receipt_doc(doc["transport"]).items():
            if isinstance(body, dict):
                assert set(doc[section]) == set(body), section
        covered = {s["name"] for s in doc["effective_settings"]}
        assert covered == set(er.TRANSPORT_SETTINGS[doc["transport"]])


# --------------------------------------------------------------------------- #
# A Converse receipt (ticket AN1b)
# --------------------------------------------------------------------------- #


def _converse_check(tmp_path: Path, doc: dict[str, Any], **kwargs: Any) -> er.ReceiptCheck:
    path = _world(tmp_path, receipt=doc)
    return er.check(er.load_receipt(path), _intended(), receipt_dir=path.parent, **kwargs)


def _setting(doc: dict[str, Any], name: str) -> dict[str, Any]:
    return next(s for s in doc["effective_settings"] if s["name"] == name)


class TestAConverseReceipt:
    def test_it_validates(self, tmp_path: Path) -> None:
        report = _converse_check(tmp_path, _converse_receipt_doc())
        assert report.green, report.lines()

    def test_the_loader_reads_the_request_not_a_cli(self, tmp_path: Path) -> None:
        receipt = er.load_receipt(_world(tmp_path, receipt=_converse_receipt_doc()))
        assert receipt.transport == CONVERSE
        assert receipt.cli is None and receipt.invocation is None
        assert receipt.request is not None
        assert receipt.request.max_tokens == 4096
        assert receipt.request.temperature == 0.0
        assert receipt.request.tool_config_present is False
        assert receipt.isolation.child_process is False

    @pytest.mark.parametrize("section", er.REQUIRED_SECTIONS[CONVERSE])
    def test_a_missing_section_is_refused(self, tmp_path: Path, section: str) -> None:
        doc = _converse_receipt_doc()
        del doc[section]
        with pytest.raises(er.ReceiptError, match=section):
            er.load_receipt(_world(tmp_path, receipt=doc))

    @pytest.mark.parametrize(
        ("section", "field"),
        _CONVERSE_SECTION_FIELDS,
        ids=[f"{s}.{f}" for s, f in _CONVERSE_SECTION_FIELDS],
    )
    def test_a_missing_field_is_refused(self, tmp_path: Path, section: str, field: str) -> None:
        doc = _converse_receipt_doc()
        del doc[section][field]
        with pytest.raises(er.ReceiptError, match=field):
            er.load_receipt(_world(tmp_path, receipt=doc))

    @pytest.mark.parametrize("section", ["cli_version", "rendered_invocation"])
    def test_cli_evidence_on_a_converse_receipt_is_refused(
        self, tmp_path: Path, section: str
    ) -> None:
        """The receipt reads the transport actually used. A CLI version or an
        argv on a Converse receipt is evidence about a run that did not
        happen."""
        doc = _converse_receipt_doc()
        doc[section] = _receipt_doc()[section]
        with pytest.raises(er.ReceiptError, match=section):
            er.load_receipt(_world(tmp_path, receipt=doc))

    def test_a_request_section_on_a_cli_receipt_is_refused(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        doc["rendered_request"] = _converse_receipt_doc()["rendered_request"]
        with pytest.raises(er.ReceiptError, match="rendered_request"):
            er.load_receipt(_world(tmp_path, receipt=doc))

    @pytest.mark.parametrize(("field", "value"), [("max_tokens", "lots"), ("max_tokens", 0.5),
                                                  ("temperature", True), ("max_tokens", 0)])
    def test_a_value_that_is_not_a_usable_number_is_refused(
        self, tmp_path: Path, field: str, value: Any
    ) -> None:
        doc = _converse_receipt_doc()
        doc["rendered_request"][field] = value
        with pytest.raises(er.ReceiptError, match=field):
            er.load_receipt(_world(tmp_path, receipt=doc))

    def test_an_unfilled_number_is_refused_as_a_placeholder(self, tmp_path: Path) -> None:
        doc = _converse_receipt_doc()
        doc["rendered_request"]["max_tokens"] = "<the maxTokens the request carries>"
        with pytest.raises(er.ReceiptError, match="placeholder"):
            er.load_receipt(_world(tmp_path, receipt=doc))


class TestWhatConverseSends:
    def test_the_table_sends_temperature_and_token_limit(self) -> None:
        """Unlike the CLI, Converse renders both into ``inferenceConfig``."""
        table = er.TRANSPORT_SETTINGS[CONVERSE]
        assert dict(table) == {"model": True, "temperature": True, "max_tokens": True}

    @pytest.mark.parametrize("name", ["temperature", "max_tokens"])
    def test_a_sent_setting_recorded_as_withheld_is_refused(
        self, tmp_path: Path, name: str
    ) -> None:
        """The CLI receipt's honest answer is the wrong one here."""
        doc = _converse_receipt_doc()
        _setting(doc, name)["transmitted"] = False
        report = _converse_check(tmp_path, doc)
        assert report.settings_recorded_as_withheld_the_transport_does_send

    @pytest.mark.parametrize(
        ("name", "value"),
        [("model", "another-model"), ("temperature", "0.7"), ("max_tokens", "1024")],
    )
    def test_a_setting_the_request_does_not_carry_is_refused(
        self, tmp_path: Path, name: str, value: str
    ) -> None:
        doc = _converse_receipt_doc()
        _setting(doc, name)["value"] = value
        report = _converse_check(tmp_path, doc)
        assert report.settings_disagree_with_the_rendered_request
        assert not report.green

    def test_an_unreadable_setting_value_disagrees(self, tmp_path: Path) -> None:
        doc = _converse_receipt_doc()
        _setting(doc, "temperature")["value"] = "zero"
        report = _converse_check(tmp_path, doc)
        assert report.settings_disagree_with_the_rendered_request

    def test_a_request_carrying_tools_is_refused(self, tmp_path: Path) -> None:
        doc = _converse_receipt_doc()
        doc["rendered_request"]["tool_config_present"] = True
        report = _converse_check(tmp_path, doc)
        assert report.invocation_missing_a_blindness_control

    @pytest.mark.parametrize("flag", ["tool_config_sent", "child_process"])
    def test_an_isolation_claim_the_transport_contradicts_is_refused(
        self, tmp_path: Path, flag: str
    ) -> None:
        doc = _converse_receipt_doc()
        doc["isolation_check"][flag] = True
        report = _converse_check(tmp_path, doc)
        assert report.isolation_contradicts_the_transport

    def test_the_freeze_cited_as_evidence_is_still_refused(self, tmp_path: Path) -> None:
        doc = _converse_receipt_doc()
        doc["isolation_check"]["evidence"] = ["the freeze passed invocation_evidence"]
        report = _converse_check(tmp_path, doc)
        assert report.isolation_evidence_citing_the_freeze

    def test_a_pin_naming_another_transport_is_refused(self, tmp_path: Path) -> None:
        doc = _converse_receipt_doc()
        doc["model_identity"]["pin"] = "claude-opus-4-8@claude-cli@2026-10-13"
        report = _converse_check(tmp_path, doc)
        assert report.model_pin_does_not_name_the_transport


def _report_of(transport: str) -> dict[str, Any]:
    """The fields of a blind report the receipt is read against."""
    if transport != CONVERSE:
        return {"assessor_transport": transport}
    return {
        "assessor_transport": transport,
        "assessor_model": CONVERSE_MODEL,
        "assessor_invocation": {
            "tool_config_sent": False,
            "child_process": False,
            "requests": 24,
            "inference_config": {"maxTokens": 4096, "temperature": 0.0},
        },
    }


class TestTheReceiptAgainstTheReport:
    """A receipt read beside the report of the run it was readiness for."""

    @pytest.mark.parametrize("transport", ["claude-cli", CONVERSE])
    def test_a_report_of_the_same_transport_agrees(self, tmp_path: Path, transport: str) -> None:
        path = _world(tmp_path, receipt=_receipt_doc(transport))
        report = er.check(
            er.load_receipt(path),
            _intended(),
            receipt_dir=path.parent,
            report=_report_of(transport),
        )
        assert report.green, report.lines()

    def test_a_report_of_another_transport_is_refused(self, tmp_path: Path) -> None:
        report = _converse_check(
            tmp_path, _converse_receipt_doc(), report={"assessor_transport": "claude-cli"}
        )
        assert report.transport_disagrees_with_the_report
        assert not report.green

    def test_a_report_naming_no_transport_is_refused(self, tmp_path: Path) -> None:
        report = _converse_check(tmp_path, _converse_receipt_doc(), report={})
        assert report.transport_disagrees_with_the_report

    def test_a_report_without_a_request_record_is_refused(self, tmp_path: Path) -> None:
        """A Converse report owes the request it measured; one carrying none
        cannot be shown to be the run the receipt describes."""
        report = _converse_check(
            tmp_path, _converse_receipt_doc(), report={"assessor_transport": CONVERSE}
        )
        assert report.request_disagrees_with_the_report

    def test_a_cli_report_is_not_compared_on_a_request(self, tmp_path: Path) -> None:
        path = _world(tmp_path, receipt=_receipt_doc())
        report = er.check(
            er.load_receipt(path), _intended(), receipt_dir=path.parent,
            report={"assessor_transport": "claude-cli"},
        )
        assert not report.request_disagrees_with_the_report

    def test_no_report_compares_nothing(self, tmp_path: Path) -> None:
        """Before the run there is no report. The receipt still validates."""
        report = _converse_check(tmp_path, _converse_receipt_doc())
        assert not report.transport_disagrees_with_the_report


# --------------------------------------------------------------------------- #
# The command
# --------------------------------------------------------------------------- #


def _bound_to_this_trees_profile(tmp_path: Path) -> tuple[Path, str]:
    """A receipt bound to the one historical profile declaration in the tree.

    The declaration is found by its schema, so this test names no instrument
    either.
    """
    found = hp.discover_declarations(REPO_ROOT)
    assert len(found) == 1, f"the tree carries {len(found)} historical declarations"
    profile = found[0]
    declaration = json.loads(profile.read_text(encoding="utf-8-sig"))
    doc = _receipt_doc()
    doc["preflight"]["profile_id"] = declaration["profile_id"]
    doc["preflight"]["profile_sha256"] = hashlib.sha256(profile.read_bytes()).hexdigest()
    preflight = _preflight_doc(profile_id=declaration["profile_id"])
    return _world(tmp_path, receipt=doc, preflight=preflight), declaration["profile_id"]


class TestTheCommand:
    def test_a_complete_receipt_exits_zero(self, tmp_path: Path, capsys: Any) -> None:
        path, _ = _bound_to_this_trees_profile(tmp_path)
        code = command.main(
            ["--receipt", str(path), "--expect-candidate", CANDIDATE, "--repo-root", str(REPO_ROOT)]
        )
        assert code == 0, capsys.readouterr().out
        assert "green" in capsys.readouterr().out

    def _report(self, tmp_path: Path, transport: str) -> Path:
        path = tmp_path / "blind_report.json"
        body = {"record_type": BLIND_REPORT_RECORD_TYPE, "assessor_transport": transport}
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def test_a_report_of_the_receipts_transport_exits_zero(
        self, tmp_path: Path, capsys: Any
    ) -> None:
        path, _ = _bound_to_this_trees_profile(tmp_path)
        report = self._report(tmp_path, "claude-cli")
        code = command.main(
            ["--receipt", str(path), "--expect-candidate", CANDIDATE,
             "--repo-root", str(REPO_ROOT), "--report", str(report)]
        )
        assert code == 0, capsys.readouterr().out

    def test_a_report_of_another_transport_exits_one(self, tmp_path: Path, capsys: Any) -> None:
        path, _ = _bound_to_this_trees_profile(tmp_path)
        report = self._report(tmp_path, CONVERSE)
        code = command.main(
            ["--receipt", str(path), "--expect-candidate", CANDIDATE,
             "--repo-root", str(REPO_ROOT), "--report", str(report)]
        )
        assert code == 1
        assert "TRANSPORT DISAGREES WITH THE REPORT" in capsys.readouterr().out

    def test_a_file_that_is_not_a_blind_report_exits_two(
        self, tmp_path: Path, capsys: Any
    ) -> None:
        path, _ = _bound_to_this_trees_profile(tmp_path)
        other = tmp_path / "other.json"
        other.write_text(json.dumps({"record_type": "something_else"}), encoding="utf-8")
        code = command.main(
            ["--receipt", str(path), "--expect-candidate", CANDIDATE,
             "--repo-root", str(REPO_ROOT), "--report", str(other)]
        )
        assert code == 2
        assert "refused" in capsys.readouterr().out

    def test_a_mismatched_candidate_exits_one(self, tmp_path: Path, capsys: Any) -> None:
        path, _ = _bound_to_this_trees_profile(tmp_path)
        code = command.main(
            [
                "--receipt",
                str(path),
                "--expect-candidate",
                "a_different_document",
                "--repo-root",
                str(REPO_ROOT),
            ]
        )
        assert code == 1
        assert "CANDIDATE BINDING MISMATCH" in capsys.readouterr().out

    def test_a_receipt_inside_the_repository_exits_two(self, capsys: Any) -> None:
        code = command.main(
            [
                "--receipt",
                "harness/execution_receipt_template.json",
                "--expect-candidate",
                CANDIDATE,
                "--repo-root",
                str(REPO_ROOT),
            ]
        )
        assert code == 2
        assert "inside the repository" in capsys.readouterr().out

    def test_a_named_profile_that_is_not_here_exits_two(
        self, tmp_path: Path, capsys: Any
    ) -> None:
        path, _ = _bound_to_this_trees_profile(tmp_path)
        code = command.main(
            [
                "--receipt",
                str(path),
                "--expect-candidate",
                CANDIDATE,
                "--expect-profile",
                "harness/profiles/absent.json",
                "--repo-root",
                str(REPO_ROOT),
            ]
        )
        assert code == 2
        assert "no profile at" in capsys.readouterr().out

    def test_the_summary_carries_no_value_the_receipt_holds(
        self, tmp_path: Path, capsys: Any
    ) -> None:
        """The operator may paste a summary where the receipt may not go."""
        path, _ = _bound_to_this_trees_profile(tmp_path)
        command.main(
            ["--receipt", str(path), "--expect-candidate", CANDIDATE, "--repo-root", str(REPO_ROOT)]
        )
        out = capsys.readouterr().out
        for private in (WORKDIR, MANIFEST, CLONE, PACK_SET, "/usr/local/bin/claude"):
            assert private not in out, private


# --------------------------------------------------------------------------- #
# The module's own contract
# --------------------------------------------------------------------------- #


class TestTheModulesOwnContract:
    def test_there_is_a_template_for_every_transport(self) -> None:
        transports = {
            json.loads((REPO_ROOT / "harness" / name).read_text(encoding="utf-8-sig"))[
                "transport"
            ]
            for name in TEMPLATES
        }
        assert transports == set(er.TRANSPORT_SETTINGS)

    def test_it_names_no_instrument(self) -> None:
        """``tests/harness/test_profile.py`` lints this over all of
        ``harness``. Asserted here too: this module's subject is one
        instrument's private run."""
        import re

        banned = re.compile(r"msca|postdoctoral|cofund|european fellowship", re.IGNORECASE)
        for module in ("harness/execution_receipt.py", "harness/commands/execution_receipt.py"):
            body = (REPO_ROOT / module).read_text(encoding="utf-8")
            assert not banned.search(body), f"{module} names an instrument"

    def test_the_findings_are_reported_one_per_line(self, tmp_path: Path) -> None:
        doc = _receipt_doc()
        doc["isolation_check"]["operating_system_sandbox"] = True
        doc["model_identity"]["attested"] = True
        report = _check(tmp_path, receipt=doc)
        assert report.findings_total == 2
        assert len(report.lines()) == 2
        assert all(":" in line for line in report.lines())
