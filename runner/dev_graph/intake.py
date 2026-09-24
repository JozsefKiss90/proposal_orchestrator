"""
Dev-graph ESR intake record — what is known about an Evaluation Summary
Report, recorded at intake and never inferred.

At intake the operator records ESR availability from the closed set
``unknown``, ``unavailable``, ``not_applicable``, ``available``; the bound
submission and call identifiers; the document the intake concerns; whether a
prior submission exists; and the permitted purpose of any ESR. The record is
read by the blind assessment lane (``harness.blind_assessment``), which
stamps the availability on its report and refuses a purpose it does not
serve. The view policies do not read it: availability never changes what a
blind package may contain.

Rules, in code:

* **Availability is declared, never derived.** An intake without a declared
  availability stores ``unknown``. A prior submission does not imply an
  available ESR (``prior_submission=True`` with nothing declared stays
  ``unknown``).
* **Available means bound.** ``available`` requires an ``esr_reference``;
  a reference without a declaration of ``available`` is refused rather than
  read as one.
* **Immutable.** One record per intake id, written once. Re-recording the
  same content is a no-op; different content under the same id is refused.
  A later change in what is known is a new intake id. No wall-clock field.

Constitutional authority:
    Subordinate to CLAUDE.md. Writes only under Tier 4 dev_graph/intake,
    evaluates no gate, invokes no Claude, invents no facts (§13.3).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runner.atomic_write import atomic_write_json
from runner.dev_graph.schema import DevGraphError

INTAKE_SCHEMA_ID = "orch.dev_graph.esr_intake.v1"

#: Repo-relative directory holding one immutable record per intake id.
INTAKE_REL = "docs/tier4_orchestration_state/dev_graph/intake"

#: The closed set of ESR availability states.
ESR_AVAILABILITY: frozenset[str] = frozenset(
    {"unknown", "unavailable", "not_applicable", "available"}
)

#: The closed set of purposes an intake may permit. A blind assessment
#: serves only the first; an ESR-informed review is a separately labelled
#: task and never shares the blind label.
PERMITTED_PURPOSES: frozenset[str] = frozenset({"blind_pre_evaluation", "esr_informed_review"})

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _refuse(kind: str, offender: str, message: str) -> DevGraphError:
    return DevGraphError(kind, offender, message)


@dataclass(frozen=True)
class EsrIntake:
    """One ESR intake record. Every field is declared by the operator."""

    intake_id: str
    document_id: str
    submission_id: str
    call_id: str
    prior_submission: bool
    esr_availability: str
    permitted_purpose: str
    esr_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": INTAKE_SCHEMA_ID,
            "intake_id": self.intake_id,
            "document_id": self.document_id,
            "submission_id": self.submission_id,
            "call_id": self.call_id,
            "prior_submission": self.prior_submission,
            "esr_availability": self.esr_availability,
            "permitted_purpose": self.permitted_purpose,
            "esr_reference": self.esr_reference,
        }


def _identifier(raw: dict[str, Any], key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise _refuse("malformed_record", where, f"{where}: {key} must be a plain identifier, got {value!r}")
    return value


def normalise_intake(raw: Any, where: str) -> EsrIntake:
    """Validate a raw intake and return the typed record, or refuse.

    Pure. ``esr_availability`` absent means ``unknown``; it is never derived
    from ``prior_submission`` or from the presence of a reference.
    """
    if not isinstance(raw, dict):
        raise _refuse("malformed_record", where, f"{where}: intake must be a JSON object")
    intake_id = _identifier(raw, "intake_id", where)
    document_id = _identifier(raw, "document_id", where)
    submission_id = _identifier(raw, "submission_id", where)
    call_id = _identifier(raw, "call_id", where)
    prior = raw.get("prior_submission", False)
    if not isinstance(prior, bool):
        raise _refuse("malformed_record", where, f"{where}: prior_submission must be a boolean")
    availability = raw.get("esr_availability")
    if availability is None:
        availability = "unknown"
    if availability not in ESR_AVAILABILITY:
        raise _refuse(
            "malformed_record",
            where,
            f"{where}: esr_availability {availability!r} is not in {sorted(ESR_AVAILABILITY)}",
        )
    purpose = raw.get("permitted_purpose")
    if purpose not in PERMITTED_PURPOSES:
        raise _refuse(
            "malformed_record",
            where,
            f"{where}: permitted_purpose {purpose!r} is not in {sorted(PERMITTED_PURPOSES)}",
        )
    reference = raw.get("esr_reference")
    if reference is not None and (not isinstance(reference, str) or not reference.strip()):
        raise _refuse("malformed_record", where, f"{where}: esr_reference must be a non-empty string or absent")
    if availability == "available" and reference is None:
        raise _refuse(
            "malformed_record",
            where,
            f"{where}: esr_availability 'available' needs an esr_reference binding the report",
        )
    if reference is not None and availability != "available":
        raise _refuse(
            "malformed_record",
            where,
            f"{where}: an esr_reference is given but esr_availability is {availability!r}, "
            "not 'available'; availability is declared, never inferred from a reference",
        )
    return EsrIntake(
        intake_id=intake_id,
        document_id=document_id,
        submission_id=submission_id,
        call_id=call_id,
        prior_submission=prior,
        esr_availability=availability,
        permitted_purpose=purpose,
        esr_reference=reference,
    )


def intake_path(repo_root: Path, intake_id: str) -> Path:
    return Path(repo_root) / INTAKE_REL / f"{intake_id}.json"


def record_esr_intake(
    repo_root: Path,
    *,
    intake_id: str,
    document_id: str,
    submission_id: str,
    call_id: str,
    permitted_purpose: str,
    prior_submission: bool = False,
    esr_availability: str | None = None,
    esr_reference: str | None = None,
) -> EsrIntake:
    """Record an ESR intake under *intake_id*; return the typed record.

    Writes once. The same content again is a no-op; different content under
    the same id is refused (``immutable_record``) and the file is untouched.
    """
    where = f"intake {intake_id}"
    record = normalise_intake(
        {
            "intake_id": intake_id,
            "document_id": document_id,
            "submission_id": submission_id,
            "call_id": call_id,
            "permitted_purpose": permitted_purpose,
            "prior_submission": prior_submission,
            "esr_availability": esr_availability,
            "esr_reference": esr_reference,
        },
        where,
    )
    target = intake_path(repo_root, record.intake_id)
    if target.is_file():
        existing = json.loads(target.read_text(encoding="utf-8-sig"))
        if existing != record.to_dict():
            raise _refuse(
                "immutable_record",
                Path(INTAKE_REL, target.name).as_posix(),
                f"intake {record.intake_id} already exists with different content; "
                "an intake record is immutable, record a new intake id",
            )
        return record
    atomic_write_json(record.to_dict(), target)
    return record


def read_esr_intake(repo_root: Path, intake_id: str) -> EsrIntake:
    """The intake record under *intake_id*, or refuse."""
    rel = Path(INTAKE_REL, f"{intake_id}.json").as_posix()
    target = intake_path(repo_root, intake_id)
    if not target.is_file():
        raise _refuse("malformed_request", str(intake_id), f"intake record {intake_id} not found at {rel}")
    try:
        raw = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise _refuse("malformed_record", rel, f"unreadable JSON: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_id") != INTAKE_SCHEMA_ID:
        raise _refuse("malformed_record", rel, f"not a {INTAKE_SCHEMA_ID} record")
    record = normalise_intake(raw, rel)
    if record.intake_id != intake_id:
        raise _refuse("malformed_record", rel, f"record names intake {record.intake_id!r}, file is {intake_id!r}")
    return record
