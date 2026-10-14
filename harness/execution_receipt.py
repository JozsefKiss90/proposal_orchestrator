"""Reading an operator's execution readiness receipt before a private run.

An assessment run inside a private environment is one nobody here can watch.
What this repository can see afterwards is the report's own declarations: a
model pin, a version tag, a transport name. Each is a string the run was told to
record. None of them is evidence that the named transport answered, that the
named settings reached it, or that the environment permitted the content to be
sent at all.

The receipt describes the transport actually used. On ``claude-cli`` that is a
CLI version and the argv handed to the operating system. On
``bedrock-converse`` no process runs, so the receipt records the request the
transport builds instead: model, temperature, token limit and the absence of a
tool configuration. Read beside the run's report, the receipt must name the
report's transport.

A readiness receipt is where the operator records that evidence, before the run
rather than after it. This module reads such a receipt and refuses one that is
incomplete, one bound to the wrong candidate or profile, and one that claims
more than its transport can deliver.

Four claims the receipt is not allowed to make:

* **That a setting reached the provider because it was configured.** A
  transport renders some settings as arguments and silently drops the rest.
  :data:`TRANSPORT_SETTINGS` records which, and a receipt disagreeing with it
  is reported rather than read charitably.
* **That a working directory is a sandbox.** A fresh directory outside every
  clone stops the assessor opening this tree. The child still runs with the
  operator's own privileges, filesystem rights and network access.
* **That the freeze verified the isolation.** The freeze reads what a report
  declares about its invocation. Verifying the invocation is a separate act,
  with a separate record, and a receipt citing a freeze condition as its own
  evidence is citing the wrong record.
* **That a model pin is attestation.** The pin is a declared identifier. The
  provider attests nothing on this path, and the receipt says so in a field
  rather than in a sentence.

What this module is not: it is not a gate, it does not run a command, and it
never writes a receipt. The receipt is the operator's, produced privately, and
nothing here copies any part of it into this repository.

This module names no instrument. The intended candidate and profile are passed
in.

Constitutional authority:
    Subordinate to CLAUDE.md. Out-of-band QA; reads a receipt and the preflight
    report it names, read-only, and writes nothing. Never a runtime gate. See
    ``harness/HARNESS.md``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from harness.blind_baseline import BASELINE_CHECKS
from harness.evidence_preflight import PREFLIGHT_RECORD_TYPE
from harness.grounding_scope import declared_scope_of
from harness.record_binding import REVIEW_STATES, STATUSES, file_sha256

__all__ = [
    "SCHEMA",
    "RECEIPT_RECORD_TYPE",
    "REQUIRED_SECTIONS",
    "TRANSPORT_SETTINGS",
    "ARGV_BLINDNESS_CONTROLS",
    "ReceiptError",
    "ProcessingRoute",
    "CliVersion",
    "ModelIdentity",
    "Setting",
    "RenderedInvocation",
    "RenderedRequest",
    "IsolationCheck",
    "Checkpoint",
    "PreflightBinding",
    "ExecutionReceipt",
    "IntendedPair",
    "ReceiptCheck",
    "load_receipt",
    "receipt_path_outside",
    "check",
    "summary_lines",
]

#: The schema this reader understands.
SCHEMA = "execution_readiness_receipt/1"

#: The ``record_type`` a receipt carries.
RECEIPT_RECORD_TYPE = "harness.execution_readiness_receipt"

_CLI = "claude-cli"
_CONVERSE = "bedrock-converse"

#: The sections a receipt covers, per transport. Each is a separate question,
#: and a receipt missing one is refused rather than read as answering it by
#: silence. The CLI's version and argv describe a child process. Converse runs
#: none, so its receipt records the request it sends instead.
REQUIRED_SECTIONS: Mapping[str, tuple[str, ...]] = {
    _CLI: (
        "processing_route",
        "cli_version",
        "model_identity",
        "effective_settings",
        "rendered_invocation",
        "isolation_check",
        "checkpoint",
        "preflight",
    ),
    _CONVERSE: (
        "processing_route",
        "model_identity",
        "effective_settings",
        "rendered_request",
        "isolation_check",
        "checkpoint",
        "preflight",
    ),
}

#: Every transport-specific section. A receipt carrying one its transport does
#: not use is refused: it would be evidence about a run that did not happen.
_TRANSPORT_SECTIONS: frozenset[str] = frozenset(
    {"cli_version", "rendered_invocation", "rendered_request"}
)

#: Which configured settings a transport actually sends. ``True`` means the
#: transport sends it; ``False`` means it is configured here and never leaves.
#:
#: On ``claude-cli`` (``runner/claude_transport.py``) the two ``False`` rows are
#: the ones a receipt is tempted to overstate. The ``claude`` CLI takes no
#: temperature argument, so the pinned temperature of 0 reaches no provider and
#: robustness comes from majority voting instead. The judge's token limit is
#: handed to ``invoke_claude_text`` and never rendered: the child's ceiling is
#: the transport's own ``CLAUDE_CODE_MAX_OUTPUT_TOKENS`` value, not the judge's.
#:
#: ``strict_mcp_config`` is sent together with the empty tool list, which is
#: the only lane a receipt describes: the transport emits ``--strict-mcp-config``
#: when, and only when, the tool list is the empty sequence. A receipt recording
#: a non-empty tool list is already reported for that, by the argv check below.
#:
#: On ``bedrock-converse`` (``runner/transport/bedrock_converse.py``) all three
#: rows are sent: ``modelId``, and ``temperature`` and ``maxTokens`` in
#: ``inferenceConfig``. Here a receipt recording either as withheld is wrong.
#:
#: Keyed by the transport names the freeze's isolation table uses, and covering
#: exactly those that owe isolation evidence.
TRANSPORT_SETTINGS: Mapping[str, Mapping[str, bool]] = {
    _CLI: {
        "model": True,
        "tools": True,
        "strict_mcp_config": True,
        "working_directory": True,
        "temperature": False,
        "max_tokens": False,
    },
    _CONVERSE: {
        "model": True,
        "temperature": True,
        "max_tokens": True,
    },
}

#: The arguments that keep an assessor blind, at the level handed to the
#: operating system. ``--tools`` must carry an empty value: ``--tools Read``
#: is an assessor that can open this tree, and omitting the flag leaves the
#: CLI's built-in tools live. ``--strict-mcp-config`` is required beside it,
#: because an empty tool list alone still exposes the operator's MCP servers
#: (measured 2026-10-05).
ARGV_BLINDNESS_CONTROLS: Mapping[str, tuple[str, ...]] = {
    _CLI: ("--tools", "--strict-mcp-config"),
}

#: An unfilled template field. A receipt carrying one is a template, and a
#: template is not evidence.
_PLACEHOLDER = re.compile(r"<[^>]*>")

#: What marks a citation of the freeze in an evidence item, and what marks a
#: freeze record among such citations.
_FREEZE_WORD = "freeze"
_FREEZE_RECORD_MARKER = ".freeze.json"


class ReceiptError(ValueError):
    """A receipt this reader refuses to read."""


# --------------------------------------------------------------------------- #
# The receipt
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ProcessingRoute:
    """What the private environment permits, and on whose authority."""

    authority: str
    processing: str
    export: str
    verified_on: str
    verified_by: str


@dataclass(frozen=True)
class CliVersion:
    """The CLI that will answer, read from the CLI rather than declared."""

    executable: str
    version_output: str
    obtained_by: str
    verified_on: str


@dataclass(frozen=True)
class ModelIdentity:
    """The model pin, and the receipt's own statement of what it is worth."""

    pin: str
    attested: bool
    note: str


@dataclass(frozen=True)
class Setting:
    """One configured setting, and whether the transport sends it."""

    name: str
    value: str
    transmitted: bool
    transport_evidence: str


@dataclass(frozen=True)
class RenderedInvocation:
    """The argv as handed to the operating system, and where it ran."""

    argv: tuple[str, ...]
    rendered_by: str
    working_directory: str


@dataclass(frozen=True)
class RenderedRequest:
    """The Converse request as the transport builds it, where no argv exists."""

    model_id: str
    temperature: float
    max_tokens: int
    tool_config_present: bool
    region: str
    rendered_by: str


@dataclass(frozen=True)
class IsolationCheck:
    """The operator's own verification, separate from any freeze record.

    The first three fields answer for every transport. The directory fields
    answer for ``claude-cli``, which runs a child. The last two answer for
    ``bedrock-converse``, which runs none and sends no tool configuration.
    """

    evidence: tuple[str, ...]
    verified_on: str
    verified_by: str
    working_directory: str = ""
    working_directory_outside_every_clone: bool = False
    operating_system_sandbox: bool = False
    tool_config_sent: bool = False
    child_process: bool = False


@dataclass(frozen=True)
class Checkpoint:
    """Where every raw response will be written as it arrives."""

    path: str
    already_exists: bool


@dataclass(frozen=True)
class PreflightBinding:
    """The preflight the run is bound to, pinned by its bytes."""

    report_path: str
    report_sha256: str
    pack_set_hash: str
    document_id: str
    profile_id: str
    profile_path: str
    profile_sha256: str
    profile_version: str
    import_manifest_path: str
    import_manifest_sha256: str
    grounding_scope: str


@dataclass(frozen=True)
class ExecutionReceipt:
    """An execution readiness receipt, parsed."""

    receipt_id: str
    authored_on: str
    review_state: str
    declared_status: str
    purpose: str
    transport: str
    private_clone_root: str
    repository_revision: str
    route: ProcessingRoute
    cli: CliVersion | None
    model: ModelIdentity
    settings: tuple[Setting, ...]
    invocation: RenderedInvocation | None
    isolation: IsolationCheck
    checkpoint: Checkpoint
    preflight: PreflightBinding
    source: str = ""
    written_by: str = ""
    #: The Converse request; ``None`` on a ``claude-cli`` receipt, whose
    #: ``cli`` and ``invocation`` are set instead.
    request: RenderedRequest | None = None

    def setting(self, name: str) -> Setting | None:
        return next((s for s in self.settings if s.name == name), None)


@dataclass(frozen=True)
class IntendedPair:
    """The Stage A pair the receipt is validated against.

    The candidate is named by the caller because the submitted original's
    document id is private. The profile is pinned by the bytes in this tree:
    the private clone sits at the revision the decision log names, so the two
    copies are the same bytes or the receipt is bound to a profile nobody here
    reviewed.
    """

    candidate_document_id: str
    profile_id: str
    profile_path: str
    profile_sha256: str


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #


def _section(raw: Mapping[str, Any], name: str, where: str) -> Mapping[str, Any]:
    if name not in raw:
        raise ReceiptError(f"{where}: the receipt carries no {name!r} section")
    body = raw[name]
    if not isinstance(body, Mapping):
        raise ReceiptError(f"{where}: {name!r} is not an object")
    return body


def _text(body: Mapping[str, Any], key: str, where: str) -> str:
    if key not in body:
        raise ReceiptError(f"{where}: {key} is missing")
    value = body[key]
    if not isinstance(value, str) or not value.strip():
        raise ReceiptError(f"{where}: {key} is empty, so it evidences nothing")
    if _PLACEHOLDER.search(value):
        raise ReceiptError(
            f"{where}: {key} is still a placeholder ({value!r}), which is not evidence"
        )
    return value.strip()


def _flag(body: Mapping[str, Any], key: str, where: str) -> bool:
    if key not in body:
        raise ReceiptError(f"{where}: {key} is missing")
    value = body[key]
    if not isinstance(value, bool):
        raise ReceiptError(f"{where}: {key} is {value!r}; the receipt answers yes or no")
    return value


def _strings(body: Mapping[str, Any], key: str, where: str) -> tuple[str, ...]:
    if key not in body:
        raise ReceiptError(f"{where}: {key} is missing")
    value = body[key]
    if not isinstance(value, (list, tuple)) or not value:
        raise ReceiptError(f"{where}: {key} is empty, so it evidences nothing")
    return tuple(str(item) for item in value)


def _number(body: Mapping[str, Any], key: str, where: str) -> float:
    if key not in body:
        raise ReceiptError(f"{where}: {key} is missing")
    value = body[key]
    if isinstance(value, str) and _PLACEHOLDER.search(value):
        raise ReceiptError(
            f"{where}: {key} is still a placeholder ({value!r}), which is not evidence"
        )
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReceiptError(f"{where}: {key} is {value!r}; the request carries a number")
    return float(value)


def _count(body: Mapping[str, Any], key: str, where: str) -> int:
    value = _number(body, key, where)
    if value != int(value) or value < 1:
        raise ReceiptError(
            f"{where}: {key} is {body[key]!r}; the request carries a positive whole number"
        )
    return int(value)


def _one_of(value: Any, allowed: tuple[str, ...], key: str, where: str) -> str:
    if value not in allowed:
        raise ReceiptError(
            f"{where}: {key} is {value!r}; expected one of {', '.join(allowed)}"
        )
    return str(value)


def load_receipt(path: Path) -> ExecutionReceipt:
    """Read a readiness receipt, fail-closed.

    Refuses a file that is not this schema, a missing section, a missing or
    empty field, an unfilled placeholder, and a transport whose settings this
    module has no table for. An absent field is never read as a negative
    answer: the operator either verified something or did not.
    """
    where = path.as_posix()
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise ReceiptError(f"{where}: not readable ({exc})") from exc
    except ValueError as exc:
        raise ReceiptError(f"{where}: not readable JSON ({exc})") from exc
    if not isinstance(raw, Mapping):
        raise ReceiptError(f"{where}: not a JSON object")
    if raw.get("schema") != SCHEMA:
        raise ReceiptError(f"{where}: schema is {raw.get('schema')!r}, expected {SCHEMA!r}")

    transport = _text(raw, "transport", where)
    if transport not in TRANSPORT_SETTINGS:
        raise ReceiptError(
            f"{where}: transport {transport!r} is not one this reader knows the sent "
            f"settings for (known: {', '.join(sorted(TRANSPORT_SETTINGS))}); a receipt "
            "cannot say what reached the provider"
        )

    required = REQUIRED_SECTIONS[transport]
    for name in sorted(_TRANSPORT_SECTIONS - set(required)):
        if name in raw:
            raise ReceiptError(
                f"{where}: the receipt carries a {name!r} section, which the {transport} "
                "transport does not produce; it is evidence about another run"
            )

    route_raw = _section(raw, "processing_route", where)
    at = f"{where}: processing_route"
    route = ProcessingRoute(
        authority=_text(route_raw, "authority", at),
        processing=_text(route_raw, "processing", at),
        export=_text(route_raw, "export", at),
        verified_on=_text(route_raw, "verified_on", at),
        verified_by=_text(route_raw, "verified_by", at),
    )

    cli: CliVersion | None = None
    if "cli_version" in required:
        cli_raw = _section(raw, "cli_version", where)
        at = f"{where}: cli_version"
        cli = CliVersion(
            executable=_text(cli_raw, "executable", at),
            version_output=_text(cli_raw, "version_output", at),
            obtained_by=_text(cli_raw, "obtained_by", at),
            verified_on=_text(cli_raw, "verified_on", at),
        )

    model_raw = _section(raw, "model_identity", where)
    at = f"{where}: model_identity"
    model = ModelIdentity(
        pin=_text(model_raw, "pin", at),
        attested=_flag(model_raw, "attested", at),
        note=_text(model_raw, "note", at),
    )

    if "effective_settings" not in raw:
        raise ReceiptError(f"{where}: the receipt carries no 'effective_settings' section")
    settings_raw = raw["effective_settings"]
    if not isinstance(settings_raw, (list, tuple)) or not settings_raw:
        raise ReceiptError(f"{where}: effective_settings covers nothing")
    settings: list[Setting] = []
    for body in settings_raw:
        if not isinstance(body, Mapping):
            raise ReceiptError(f"{where}: effective_settings holds a non-object entry")
        at = f"{where}: effective_settings entry"
        name = _text(body, "name", at)
        at = f"{where}: setting {name}"
        if "value" not in body:
            raise ReceiptError(f"{at}: value is missing")
        settings.append(
            Setting(
                name=name,
                value=str(body["value"]),
                transmitted=_flag(body, "transmitted", at),
                transport_evidence=_text(body, "transport_evidence", at),
            )
        )

    invocation: RenderedInvocation | None = None
    if "rendered_invocation" in required:
        invocation_raw = _section(raw, "rendered_invocation", where)
        at = f"{where}: rendered_invocation"
        # The argv is read verbatim, placeholder rule and all: it is what the
        # transport rendered, and a rubric prompt carries whatever it carries.
        argv = _strings(invocation_raw, "argv", at)
        invocation = RenderedInvocation(
            argv=argv,
            rendered_by=_text(invocation_raw, "rendered_by", at),
            working_directory=_text(invocation_raw, "working_directory", at),
        )

    request: RenderedRequest | None = None
    if "rendered_request" in required:
        request_raw = _section(raw, "rendered_request", where)
        at = f"{where}: rendered_request"
        request = RenderedRequest(
            model_id=_text(request_raw, "model_id", at),
            temperature=_number(request_raw, "temperature", at),
            max_tokens=_count(request_raw, "max_tokens", at),
            tool_config_present=_flag(request_raw, "tool_config_present", at),
            region=_text(request_raw, "region", at),
            rendered_by=_text(request_raw, "rendered_by", at),
        )

    isolation_raw = _section(raw, "isolation_check", where)
    at = f"{where}: isolation_check"
    evidence = _strings(isolation_raw, "evidence", at)
    verified_on = _text(isolation_raw, "verified_on", at)
    verified_by = _text(isolation_raw, "verified_by", at)
    if transport == _CONVERSE:
        isolation = IsolationCheck(
            evidence=evidence,
            verified_on=verified_on,
            verified_by=verified_by,
            tool_config_sent=_flag(isolation_raw, "tool_config_sent", at),
            child_process=_flag(isolation_raw, "child_process", at),
        )
    else:
        isolation = IsolationCheck(
            evidence=evidence,
            verified_on=verified_on,
            verified_by=verified_by,
            working_directory=_text(isolation_raw, "working_directory", at),
            working_directory_outside_every_clone=_flag(
                isolation_raw, "working_directory_outside_every_clone", at
            ),
            operating_system_sandbox=_flag(isolation_raw, "operating_system_sandbox", at),
        )

    checkpoint_raw = _section(raw, "checkpoint", where)
    at = f"{where}: checkpoint"
    checkpoint = Checkpoint(
        path=_text(checkpoint_raw, "path", at),
        already_exists=_flag(checkpoint_raw, "already_exists", at),
    )

    preflight_raw = _section(raw, "preflight", where)
    at = f"{where}: preflight"
    preflight = PreflightBinding(
        report_path=_text(preflight_raw, "report_path", at),
        report_sha256=_text(preflight_raw, "report_sha256", at),
        pack_set_hash=_text(preflight_raw, "pack_set_hash", at),
        document_id=_text(preflight_raw, "document_id", at),
        profile_id=_text(preflight_raw, "profile_id", at),
        profile_path=_text(preflight_raw, "profile_path", at),
        profile_sha256=_text(preflight_raw, "profile_sha256", at),
        profile_version=_text(preflight_raw, "profile_version", at),
        import_manifest_path=_text(preflight_raw, "import_manifest_path", at),
        import_manifest_sha256=_text(preflight_raw, "import_manifest_sha256", at),
        grounding_scope=_text(preflight_raw, "grounding_scope", at),
    )

    return ExecutionReceipt(
        receipt_id=_text(raw, "receipt_id", where),
        authored_on=_text(raw, "authored_on", where),
        review_state=_one_of(
            raw.get("review_state"), REVIEW_STATES, "review_state", where
        ),
        declared_status=_one_of(
            raw.get("declared_status"), STATUSES, "declared_status", where
        ),
        purpose=_text(raw, "purpose", where),
        transport=transport,
        private_clone_root=_text(raw, "private_clone_root", where),
        repository_revision=_text(raw, "repository_revision", where),
        route=route,
        cli=cli,
        model=model,
        settings=tuple(settings),
        invocation=invocation,
        isolation=isolation,
        checkpoint=checkpoint,
        preflight=preflight,
        source=where,
        written_by=_text(raw, "written_by", where),
        request=request,
    )


def receipt_path_outside(path: Path, repo_root: Path) -> Path:
    """Return *path*, having confirmed it does not lie inside *repo_root*.

    The receipt holds private paths, a private clone's revision and the
    operator's own verification acts. None of that enters this repository, so
    the command that reads a receipt refuses one stored here — measured against
    the root, the way the subscription judge measures its working directory.
    """
    try:
        inside = path.resolve().is_relative_to(repo_root.resolve())
    except (OSError, ValueError) as exc:  # pragma: no cover - platform-dependent
        raise ReceiptError(
            f"{path.as_posix()} cannot be compared with the repository root: {exc}"
        ) from exc
    if inside:
        raise ReceiptError(
            f"{path.as_posix()} lies inside the repository. A receipt is the private "
            "operator's record and stays outside this tree; keep it in the private "
            "environment and name it there"
        )
    return path


# --------------------------------------------------------------------------- #
# Paths, compared without resolving them
# --------------------------------------------------------------------------- #


def _parts(path: str) -> tuple[str, ...]:
    """*path*'s segments, separator- and case-normalised.

    The paths in a receipt are a private machine's, so none of them exists
    here and none can be resolved. They are compared as written, with
    backslashes read as separators and case folded, because the environment
    may be either platform.
    """
    normalised = PurePosixPath(str(path).replace("\\", "/"))
    return tuple(part.lower() for part in normalised.parts if part not in ("", "."))


def _under(root: str, path: str) -> bool | None:
    """Whether *path* lies under *root*. ``None`` when either is empty."""
    root_parts = _parts(root)
    path_parts = _parts(path)
    if not root_parts or not path_parts:
        return None
    return path_parts[: len(root_parts)] == root_parts


# --------------------------------------------------------------------------- #
# The check
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ReceiptCheck:
    """A receipt read against the intended pair and against its transport."""

    candidate_binding_mismatch: tuple[str, ...] = ()
    profile_binding_mismatch: tuple[str, ...] = ()
    settings_the_receipt_does_not_cover: tuple[str, ...] = ()
    settings_claimed_transmitted_the_transport_does_not_send: tuple[str, ...] = ()
    settings_recorded_as_withheld_the_transport_does_send: tuple[str, ...] = ()
    settings_disagree_with_the_rendered_request: tuple[str, ...] = ()
    invocation_missing_a_blindness_control: tuple[str, ...] = ()
    invocation_working_directory_disagrees: tuple[str, ...] = ()
    isolation_contradicts_the_transport: tuple[str, ...] = ()
    isolation_claims_a_sandbox: tuple[str, ...] = ()
    isolation_not_outside_every_clone: tuple[str, ...] = ()
    isolation_working_directory_inside_the_clone: tuple[str, ...] = ()
    isolation_evidence_citing_the_freeze: tuple[str, ...] = ()
    cli_version_not_obtained_from_the_cli: tuple[str, ...] = ()
    model_pin_claimed_attested: tuple[str, ...] = ()
    model_pin_does_not_name_the_transport: tuple[str, ...] = ()
    checkpoint_outside_the_clone: tuple[str, ...] = ()
    checkpoint_already_exists: tuple[str, ...] = ()
    preflight_unreadable: tuple[str, ...] = ()
    preflight_incomplete: tuple[str, ...] = ()
    preflight_disagrees_with_the_receipt: tuple[str, ...] = ()
    transport_disagrees_with_the_report: tuple[str, ...] = ()
    request_disagrees_with_the_report: tuple[str, ...] = ()

    @property
    def green(self) -> bool:
        return not any(getattr(self, f) for f in self.__dataclass_fields__)

    @property
    def findings_total(self) -> int:
        return sum(len(getattr(self, f)) for f in self.__dataclass_fields__)

    def lines(self) -> tuple[str, ...]:
        out: list[str] = []
        for attr in self.__dataclass_fields__:
            label = attr.replace("_", " ").upper()
            for item in getattr(self, attr):
                out.append(f"{label}: {item}")
        return tuple(out)


def _check_settings(receipt: ExecutionReceipt, found: dict[str, list[str]]) -> None:
    table = TRANSPORT_SETTINGS[receipt.transport]
    for name, sent in table.items():
        setting = receipt.setting(name)
        if setting is None:
            found["settings_the_receipt_does_not_cover"].append(name)
            continue
        if setting.transmitted and not sent:
            found["settings_claimed_transmitted_the_transport_does_not_send"].append(
                f"{name} is recorded as transmitted; the {receipt.transport} transport "
                f"renders no such argument ({setting.transport_evidence})"
            )
        elif sent and not setting.transmitted:
            found["settings_recorded_as_withheld_the_transport_does_send"].append(
                f"{name} is recorded as not transmitted; the {receipt.transport} "
                "transport does send it"
            )


def _check_invocation(receipt: ExecutionReceipt, found: dict[str, list[str]]) -> None:
    if receipt.request is not None:
        _check_request(receipt, receipt.request, found)
    if receipt.invocation is not None:
        _check_argv(receipt, receipt.invocation, found)


def _setting_number(setting: Setting) -> float | None:
    try:
        return float(setting.value)
    except ValueError:
        return None


def _check_request(
    receipt: ExecutionReceipt, request: RenderedRequest, found: dict[str, list[str]]
) -> None:
    """The Converse request carries no tools, and carries the recorded settings.

    The settings table says *that* a setting is sent. The rendered request says
    *what* was sent, so a receipt whose settings name other values describes a
    request nobody built.
    """
    if request.tool_config_present:
        found["invocation_missing_a_blindness_control"].append(
            "the rendered request carries a toolConfig; a blind assessor's request "
            "carries none"
        )
    sent = {
        "model": request.model_id,
        "temperature": request.temperature,
        "max_tokens": float(request.max_tokens),
    }
    for name, value in sent.items():
        setting = receipt.setting(name)
        if setting is None:
            continue  # reported as uncovered by the settings check
        recorded: Any = setting.value if name == "model" else _setting_number(setting)
        if recorded != value:
            found["settings_disagree_with_the_rendered_request"].append(
                f"{name} is recorded as {setting.value!r}, and the rendered request "
                f"carries {value!r}"
            )


def _check_argv(
    receipt: ExecutionReceipt, invocation: RenderedInvocation, found: dict[str, list[str]]
) -> None:
    argv = list(invocation.argv)
    for control in ARGV_BLINDNESS_CONTROLS[receipt.transport]:
        if control not in argv:
            found["invocation_missing_a_blindness_control"].append(
                f"the rendered argv carries no {control}"
            )
            continue
        if control != "--tools":
            continue
        at = argv.index(control) + 1
        value = argv[at] if at < len(argv) else "(nothing)"
        if value.strip().strip('"').strip("'"):
            found["invocation_missing_a_blindness_control"].append(
                f"the rendered argv carries --tools {value!r}; a blind assessor's tool "
                "list is empty"
            )
    if _parts(invocation.working_directory) != _parts(receipt.isolation.working_directory):
        found["invocation_working_directory_disagrees"].append(
            "the verified directory and the directory the invocation ran in are not "
            "the same directory"
        )


def _check_isolation(receipt: ExecutionReceipt, found: dict[str, list[str]]) -> None:
    if receipt.transport == _CONVERSE:
        _check_converse_isolation(receipt, found)
    else:
        _check_directory_isolation(receipt, found)
    _check_evidence_source(receipt, found)


def _check_converse_isolation(receipt: ExecutionReceipt, found: dict[str, list[str]]) -> None:
    """Converse runs no process and sends no tools. A receipt saying otherwise
    describes a run this transport did not make."""
    if receipt.isolation.tool_config_sent:
        found["isolation_contradicts_the_transport"].append(
            "the receipt records a tool configuration sent; the blind Converse "
            "request sends none"
        )
    if receipt.isolation.child_process:
        found["isolation_contradicts_the_transport"].append(
            "the receipt records a child process; Converse is an API call and runs none"
        )


def _check_directory_isolation(receipt: ExecutionReceipt, found: dict[str, list[str]]) -> None:
    if receipt.isolation.operating_system_sandbox:
        found["isolation_claims_a_sandbox"].append(
            "the receipt claims an operating-system sandbox. A fresh directory outside "
            "every clone is not one: the child runs with the operator's own privileges, "
            "filesystem rights and network access"
        )
    if not receipt.isolation.working_directory_outside_every_clone:
        found["isolation_not_outside_every_clone"].append(
            "the working directory is not declared outside every clone, so the assessor "
            "is not shown to be blind to this tree"
        )
    inside = _under(receipt.private_clone_root, receipt.isolation.working_directory)
    if inside:
        found["isolation_working_directory_inside_the_clone"].append(
            f"the working directory lies under the private clone "
            f"{receipt.private_clone_root}"
        )


def _check_evidence_source(receipt: ExecutionReceipt, found: dict[str, list[str]]) -> None:
    for item in receipt.isolation.evidence:
        # The freeze is never where the isolation was verified, so an evidence
        # item citing it is the defect — whether or not it names a condition.
        # Keyed on the citation rather than on a condition name alone: a
        # condition name is an ordinary word, and "assessor_transport" can
        # appear in evidence that cites no freeze at all.
        if _FREEZE_WORD not in item.lower():
            continue
        named = sorted(c for c in BASELINE_CHECKS if c in item)
        what = f"the freeze condition {named[0]!r}" if named else "the freeze"
        if not named and _FREEZE_RECORD_MARKER in item:
            what = "a freeze record"
        found["isolation_evidence_citing_the_freeze"].append(
            f"{item!r} cites {what}. The freeze reads what a report declares about its "
            "invocation; verifying that invocation is this receipt's own act"
        )


def _check_pins(receipt: ExecutionReceipt, found: dict[str, list[str]]) -> None:
    if receipt.cli is not None and "--version" not in receipt.cli.obtained_by:
        found["cli_version_not_obtained_from_the_cli"].append(
            f"the version was obtained by {receipt.cli.obtained_by!r}; a version string "
            "is runtime evidence only where the CLI printed it"
        )
    if receipt.model.attested:
        found["model_pin_claimed_attested"].append(
            "the model pin is recorded as attested. It is a declared identifier, and "
            "the provider attests nothing on this transport"
        )
    if receipt.transport not in receipt.model.pin:
        found["model_pin_does_not_name_the_transport"].append(
            f"the pin {receipt.model.pin!r} does not name the {receipt.transport} "
            "transport, so a report carrying it would carry this transport under "
            "another name"
        )


def _check_checkpoint(receipt: ExecutionReceipt, found: dict[str, list[str]]) -> None:
    if receipt.checkpoint.already_exists:
        found["checkpoint_already_exists"].append(
            f"{receipt.checkpoint.path} already exists. An existing checkpoint is never "
            "appended to, so the run would refuse after the quota was spent"
        )
    under = _under(receipt.private_clone_root, receipt.checkpoint.path)
    if under is False:
        found["checkpoint_outside_the_clone"].append(
            f"{receipt.checkpoint.path} does not lie under the private clone "
            f"{receipt.private_clone_root}; the run writes its checkpoint under the "
            "repository root, never under the output directory"
        )


def _resolve_preflight(binding: PreflightBinding, receipt_dir: Path | None) -> Path | None:
    candidates = [Path(binding.report_path)]
    if receipt_dir is not None:
        candidates.append(receipt_dir / binding.report_path)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _check_preflight(
    receipt: ExecutionReceipt, receipt_dir: Path | None, found: dict[str, list[str]]
) -> None:
    """Read the preflight the receipt names, rather than trust what it says.

    The receipt's own preflight block is a copy of figures the report already
    carries. Reading the report back is what makes the copy evidence: a
    receipt bound to a report whose bytes, candidate, profile, pack set,
    manifest or scope are not the ones it records is bound to a different run.
    """
    binding = receipt.preflight
    path = _resolve_preflight(binding, receipt_dir)
    if path is None:
        found["preflight_unreadable"].append(
            f"{binding.report_path} is not readable from here. Validate the receipt "
            "where its preflight report is"
        )
        return
    if file_sha256(path) != binding.report_sha256:
        found["preflight_disagrees_with_the_receipt"].append(
            f"{binding.report_path} does not hash to the recorded "
            f"{binding.report_sha256[:12]}; the receipt pins other bytes"
        )
        return
    try:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        found["preflight_unreadable"].append(f"{binding.report_path}: {exc}")
        return
    if not isinstance(report, Mapping):
        found["preflight_incomplete"].append(f"{binding.report_path} is not a JSON object")
        return

    if report.get("record_type") != PREFLIGHT_RECORD_TYPE:
        found["preflight_incomplete"].append(
            f"{binding.report_path} is a {report.get('record_type')!r} record, not a "
            f"{PREFLIGHT_RECORD_TYPE}"
        )
        return

    manifest = report.get("import_manifest")
    if not isinstance(manifest, Mapping) or not manifest.get("path"):
        found["preflight_incomplete"].append(
            "the preflight names no import manifest. The manifest is named explicitly, "
            "and the resolver's predecessor default is never relied on"
        )
    else:
        if _parts(str(manifest.get("path"))) != _parts(binding.import_manifest_path):
            found["preflight_disagrees_with_the_receipt"].append(
                f"the preflight's manifest is {manifest.get('path')!r}, and the receipt "
                f"records {binding.import_manifest_path!r}"
            )
        if str(manifest.get("sha256") or "") != binding.import_manifest_sha256:
            found["preflight_disagrees_with_the_receipt"].append(
                "the preflight's manifest hash is not the one the receipt records"
            )

    # An insufficient_context pack is not among these. The pack set records it
    # as an explicit outcome, and a rubric graded on one must not read as a
    # clean pass; refusing it here would refuse a declared result. What is
    # incomplete is a report that selected nothing at all.
    for key in ("packs", "criterion_inputs"):
        selected = report.get(key)
        if not isinstance(selected, (list, tuple)) or not selected:
            found["preflight_incomplete"].append(
                f"the preflight realised no {key}, so the run it binds would read no "
                "evidence"
            )

    scope = declared_scope_of(report)
    if scope is None:
        found["preflight_incomplete"].append(
            "the preflight declares no grounding scope, so what the run could judge is "
            "unstated"
        )
    elif scope != binding.grounding_scope:
        found["preflight_disagrees_with_the_receipt"].append(
            f"the preflight declares scope {scope!r}, and the receipt "
            f"records {binding.grounding_scope!r}"
        )

    for key, recorded in (
        ("document_id", binding.document_id),
        ("profile_id", binding.profile_id),
        ("profile_version", binding.profile_version),
        ("pack_set_hash", binding.pack_set_hash),
    ):
        actual = str(report.get(key) or "")
        if not actual:
            found["preflight_incomplete"].append(f"the preflight carries no {key}")
        elif actual != recorded:
            found["preflight_disagrees_with_the_receipt"].append(
                f"the preflight's {key} is {actual!r}, and the receipt records "
                f"{recorded!r}"
            )


def _check_bindings(
    receipt: ExecutionReceipt, intended: IntendedPair, found: dict[str, list[str]]
) -> None:
    if receipt.preflight.document_id != intended.candidate_document_id:
        found["candidate_binding_mismatch"].append(
            f"the receipt is bound to candidate {receipt.preflight.document_id!r}; the "
            f"intended Stage A candidate is {intended.candidate_document_id!r}"
        )
    if receipt.preflight.profile_id != intended.profile_id:
        found["profile_binding_mismatch"].append(
            f"the receipt is bound to profile {receipt.preflight.profile_id!r}; the "
            f"intended Stage A profile is {intended.profile_id!r}"
        )
    if receipt.preflight.profile_sha256 != intended.profile_sha256:
        found["profile_binding_mismatch"].append(
            f"the receipt pins profile bytes {receipt.preflight.profile_sha256[:12]}; "
            f"{intended.profile_path} in this tree hashes to "
            f"{intended.profile_sha256[:12]}"
        )


def _check_report(
    receipt: ExecutionReceipt, report: Mapping[str, Any], found: dict[str, list[str]]
) -> None:
    """The report of the run names the transport this receipt was evidence for."""
    actual = str(report.get("assessor_transport") or "")
    if not actual:
        found["transport_disagrees_with_the_report"].append(
            "the report names no assessor_transport, so the receipt cannot be shown "
            "to describe its run"
        )
    elif actual != receipt.transport:
        found["transport_disagrees_with_the_report"].append(
            f"the report's run spoke {actual}; the receipt is evidence for "
            f"{receipt.transport}"
        )
    elif receipt.request is not None:
        _check_request_against_report(receipt.request, report, found)


def _check_request_against_report(
    request: RenderedRequest, report: Mapping[str, Any], found: dict[str, list[str]]
) -> None:
    """The request the run measured is the request the receipt recorded.

    The Converse backend records the ``inferenceConfig`` of every request it
    sent (``assessor_invocation``). A receipt naming another model, token
    limit or temperature describes a request this run did not send.
    """
    key = "request_disagrees_with_the_report"
    model = str(report.get("assessor_model") or "")
    if model != request.model_id:
        found[key].append(
            f"the report's assessor model is {model!r}; the receipt's request carries "
            f"{request.model_id!r}"
        )
    invocation = report.get("assessor_invocation")
    sent = invocation.get("inference_config") if isinstance(invocation, Mapping) else None
    if not isinstance(sent, Mapping):
        found[key].append(
            "the report records no single inferenceConfig, so the request the run sent "
            "cannot be compared with the receipt's"
        )
        return
    for name, recorded in (("temperature", request.temperature), ("maxTokens", request.max_tokens)):
        value = sent.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != recorded:
            found[key].append(
                f"the run sent {name}={value!r}; the receipt's request carries {recorded!r}"
            )


def check(
    receipt: ExecutionReceipt,
    intended: IntendedPair,
    *,
    receipt_dir: Path | None = None,
    report: Mapping[str, Any] | None = None,
) -> ReceiptCheck:
    """Read *receipt* against *intended* and against what its transport sends.

    *receipt_dir* is where a relative preflight path is resolved from, which is
    the directory the receipt itself was read from. Absent it, only an absolute
    preflight path resolves, and a report that does not resolve is a finding
    rather than a silent pass.

    *report* is the blind report of the run, once it exists. Its transport
    must be the receipt's. Before the run there is none, and nothing is
    compared.

    Named ``check`` for the same reason the sibling readers are: it reports what
    does not hold and settles nothing.
    """
    found: dict[str, list[str]] = {
        field: [] for field in ReceiptCheck.__dataclass_fields__
    }
    _check_bindings(receipt, intended, found)
    _check_settings(receipt, found)
    _check_invocation(receipt, found)
    _check_isolation(receipt, found)
    _check_pins(receipt, found)
    _check_checkpoint(receipt, found)
    _check_preflight(receipt, receipt_dir, found)
    if report is not None:
        _check_report(receipt, report, found)
    return ReceiptCheck(**{key: tuple(value) for key, value in found.items()})


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def summary_lines(receipt: ExecutionReceipt, report: ReceiptCheck) -> tuple[str, ...]:
    """The validator's own summary, for the operator's terminal.

    Field names, counts and verdicts. No value the receipt carries, because the
    operator may paste this where the receipt may not go.
    """
    sent = tuple(s.name for s in receipt.settings if s.transmitted)
    if receipt.transport == _CONVERSE:
        claim = f"tool config sent: {receipt.isolation.tool_config_sent}"
    else:
        claim = f"sandbox: {receipt.isolation.operating_system_sandbox}"
    lines = [
        f"receipt:      {receipt.receipt_id}",
        f"transport:    {receipt.transport}",
        f"settings:     {len(receipt.settings)} covered, {len(sent)} transmitted",
        f"isolation:    verified {receipt.isolation.verified_on}, "
        f"{len(receipt.isolation.evidence)} piece(s) of evidence, {claim}",
        f"preflight:    {'read' if not report.preflight_unreadable else 'not readable'}",
    ]
    if report.green:
        lines.append("receipt check: green")
    else:
        lines.extend(report.lines())
        lines.append(f"receipt check: {report.findings_total} finding(s)")
    return tuple(lines)
