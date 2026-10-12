"""The open-deferral register of the 2026-10-08 approval, derived from its records.

The approval of 2026-10-08 settled some things and left others open. A ticket
checkbox holds none of them, and a milestone that accepts the package inherits
every one. This module writes the register that stops that: one row per open
item, each naming its owner, the evidence that would close it, and whether that
evidence requires the submitted original.

What this module is
-------------------
A deterministic, Claude-free transform, in the shape of
:mod:`tools.author_approved_dispositions`. Every row is *derived* from a
committed record rather than typed:

* the ten rows the approval deferred to the private network, and the ten
  carrying an agent's declaration it did not address, come from the approved
  dispositions' own ``decision_state`` lists;
* the two rows whose disposition is confirmed and whose interpretation stays
  open are the intersection of ``rows_operator_confirmed`` with
  ``open_operator_decisions`` — ESR-Q-01 and ESR-Q-03, computed and not named
  here;
* the unresolved disposition marker is every row whose ``declared_status`` is
  ``Unresolved`` — ESR-E-04, likewise computed;
* the two assessor validation cases are the record's own
  ``assessor_validation_cases``, and each one's ``original_required`` is read
  off its recorded limit;
* the eight original-dependent questions are parsed from the approval record's
  own deferred table;
* the one open ticket criterion is read from the predecessor ledger, which this
  module refuses to render against if the box has since been checked.

So the row set is a measurement of the records. Adding a row means a record
changed, and :func:`check` then reports the register stale rather than letting
the two drift.

What this module does not do
----------------------------
It closes nothing, confirms no evidence, and edits none of the records it reads.
Every row is written ``open``, because closing one needs evidence this
repository does not yet hold. The approval record, the dispositions, the
revision plan, the ESR record and the integrity audits are bound by sha256 as
immutable evidence; the predecessor ledger is bound as a tracked input, since a
ticket is allowed to move.

It also does not check its own output, and cannot: ``harness/`` holds the reader
and this package may not import it, under the one-way boundary
``tests/harness/test_boundary.py`` enforces. That split is the right one anyway
— a tool that both wrote a record and certified it would be judging its own
output. ``harness.commands.deferral_register`` reads the register, writes the
Markdown reading beside it, and is the command that can fail.

Usage::

    py -3.10 -m tools.author_deferral_register           # write the register
    py -3.10 -m tools.author_deferral_register --check   # byte-equal replay

Then check it and render its reading, with the path the write prints::

    py -3.10 -m harness.commands.deferral_register --register <REGISTER_REL>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.paths import find_repo_root
from tools.fidelity_declarations import file_sha256

# --------------------------------------------------------------------------- #
# The records this register reads
# --------------------------------------------------------------------------- #

DN_DIR = Path("docs/tier4_orchestration_state/msca_dn")

APPROVAL_REL = DN_DIR / "reviews/operator_approval_2026-10-08.md"
DISPOSITIONS_REL = DN_DIR / "esr/dispositions_f60ae6e0a2a1_approved.json"
REVISIONS_REL = DN_DIR / "comparisons/revisions_f60ae6e0a2a1_0003.json"
ESR_REL = DN_DIR / "esr/msca-dn-2025-esr.json"
AUDIT_R03_REL = DN_DIR / "audit/integrity_242f1afb02c8_0001.json"
AUDIT_R04_REL = DN_DIR / "audit/integrity_242f1afb02c8_0002.json"
AUDIT_APPROVED_REL = DN_DIR / "audit/integrity_242f1afb02c8_0003.json"
LEDGER_REL = Path("plans/pe08_review_and_pe09_handoff_tickets.md")

REGISTER_REL = DN_DIR / "deferrals/open_deferral_register_2026-10-12.json"

#: The schema the register declares. ``harness.deferral_register.SCHEMA`` is the
#: reader's copy, and ``tests/test_msca_dn_deferral_register.py`` asserts the two
#: agree. Deliberate double entry: this module may not import the harness, which
#: is the one-way boundary ``tests/harness/test_boundary.py`` enforces.
SCHEMA = "deferral_register/1"

#: The heading of the approval record's original-dependent table.
DEFERRED_TABLE_HEADING = "## Original-dependent decisions explicitly deferred"

#: The R04 acceptance criterion that stays unchecked, quoted from the ledger.
R04_CRITERION = "Draft declarations survive the supported generation workflow after adoption."

#: The decision that defers the criterion's own precondition.
R04_PRECONDITION = (
    "D13 defers adoption of the R04 declaration drafts into an active register, so the "
    "criterion's precondition is unmet. The box is not checkable and not failing."
)

AUTHORED_ON = "2026-10-12"
TICKET = "V11 of plans/msca_dn_historical_validation_tickets.md"


class DeferralAuthoringError(RuntimeError):
    """A record this module refuses to render against."""


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _one_line(text: str) -> str:
    return " ".join(str(text).split())


def _esr_kind(esr: Mapping[str, Any], observation_id: str) -> str:
    for observation in esr.get("observations", ()):
        if observation.get("id") == observation_id:
            return str(observation.get("kind") or "")
    raise DeferralAuthoringError(f"{ESR_REL}: no observation {observation_id}")


def _esr_ids(esr: Mapping[str, Any]) -> frozenset[str]:
    return frozenset(str(o["id"]) for o in esr.get("observations", ()))


def _normalised_observations(cell: str, known: frozenset[str]) -> tuple[str, ...]:
    """The observation ids a table cell names, in the evaluation summary's
    namespace.

    The approval prose writes ``E-02, E-04, E-08`` where the records write
    ``ESR-E-02``. Normalising here is what makes the register's cross-reference
    table find the overlap between a deferred question and the disposition row
    over the same observation. A token that names no observation - ``M7.3 and
    appointments`` - is left out rather than coerced.
    """
    found: list[str] = []
    for token in cell.split(","):
        token = token.strip()
        for candidate in (token, f"ESR-{token}"):
            if candidate in known and candidate not in found:
                found.append(candidate)
                break
    return tuple(found)


def _deferred_table(approval_text: str) -> tuple[dict[str, str], ...]:
    """The approval record's original-dependent table, row by row.

    Three columns, in the record's own order. The header and rule rows are
    dropped; a row with another shape is refused rather than guessed at, since
    the register's eighth group is this table and nothing else.
    """
    if DEFERRED_TABLE_HEADING not in approval_text:
        raise DeferralAuthoringError(f"{APPROVAL_REL}: no {DEFERRED_TABLE_HEADING!r} section")
    section = approval_text.split(DEFERRED_TABLE_HEADING, 1)[1].split("\n## ", 1)[0]
    rows: list[dict[str, str]] = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 3:
            raise DeferralAuthoringError(
                f"{APPROVAL_REL}: the deferred table has a {len(cells)}-column row: {line}"
            )
        if cells[0] == "Observations" or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append(
            {"observations": cells[0], "evidence": cells[1], "disposition": cells[2]}
        )
    if not rows:
        raise DeferralAuthoringError(f"{APPROVAL_REL}: the deferred table has no rows")
    return tuple(rows)


def _r04_criterion_line(ledger_text: str) -> str:
    """The R04 criterion line, refused if the box has been checked.

    The register row exists because the box is unchecked. If the ledger checks
    it, the row has to close with its evidence, and that is a decision this
    module may not make for a reader.
    """
    for line in ledger_text.splitlines():
        if R04_CRITERION in line:
            if line.strip().startswith("- [x]"):
                raise DeferralAuthoringError(
                    f"{LEDGER_REL}: the R04 criterion is now checked; close the register row "
                    "with its evidence instead of re-deriving it as open"
                )
            if not line.strip().startswith("- [ ]"):
                raise DeferralAuthoringError(
                    f"{LEDGER_REL}: the R04 criterion is not a checkbox line: {line.strip()}"
                )
            return _one_line(line.strip()[5:])
    raise DeferralAuthoringError(f"{LEDGER_REL}: no line carries {R04_CRITERION!r}")


# --------------------------------------------------------------------------- #
# Deriving the rows
# --------------------------------------------------------------------------- #


def _deferral_index(dispositions: Mapping[str, Any]) -> dict[str, tuple[int, dict[str, Any]]]:
    """Each deferred observation mapped to its position and entry."""
    found: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, entry in enumerate(dispositions["open_operator_decisions"]):
        found[str(entry["observation_id"])] = (index, dict(entry))
    return found


def _row_index(dispositions: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(r["observation_id"]): dict(r) for r in dispositions["rows"]}


def _closure_from_deferral(entry: Mapping[str, Any]) -> str:
    return _one_line(
        f"{entry['required_private_evidence']} The approval's disposition stands until then: "
        f"{entry['current_review_disposition']}"
    )


def _operator_decision_rows(
    dispositions: Mapping[str, Any], esr: Mapping[str, Any]
) -> list[dict[str, Any]]:
    deferrals = _deferral_index(dispositions)
    rows = _row_index(dispositions)
    out: list[dict[str, Any]] = []
    for observation_id in dispositions["decision_state"]["rows_operator_decision_required"]:
        if observation_id not in deferrals:
            raise DeferralAuthoringError(
                f"{DISPOSITIONS_REL}: {observation_id} is deferred and names no required evidence"
            )
        index, entry = deferrals[observation_id]
        row = rows[observation_id]
        out.append(
            {
                "id": f"ODR-{observation_id}",
                "kind": "operator_decision_required",
                "observation_ids": (observation_id,),
                "subject": _one_line(
                    f"{observation_id} ({_esr_kind(esr, observation_id)}) is declared "
                    f"{row['disposition']} with status {row['declared_status']}. The approval "
                    "deferred the row to the private network, so its disposition is not settled."
                ),
                "owner": "the private operator",
                "closure_evidence": _closure_from_deferral(entry),
                "original_required": True,
                "source": f"{DISPOSITIONS_REL.as_posix()}#open_operator_decisions/#{index}",
            }
        )
    return out


def _agent_recommendation_rows(
    dispositions: Mapping[str, Any], esr: Mapping[str, Any]
) -> list[dict[str, Any]]:
    rows = _row_index(dispositions)
    listed = dispositions["decision_state"]["rows_agent_recommended"]
    out: list[dict[str, Any]] = []
    for index, observation_id in enumerate(listed):
        row = rows[observation_id]
        out.append(
            {
                "id": f"AGR-{observation_id}",
                "kind": "agent_recommendation",
                "observation_ids": (observation_id,),
                "subject": _one_line(
                    f"{observation_id} ({_esr_kind(esr, observation_id)}) carries the agent's "
                    f"declaration {row['disposition']} with status {row['declared_status']}. The "
                    "approval addressed no decision to it."
                ),
                "owner": "the operator",
                "closure_evidence": _one_line(
                    "An operator decision on this row, recorded in a successor review record. "
                    "The approval states that the other agent-drafted observations are not "
                    "blanket-confirmed by it, so silence is not confirmation."
                ),
                "original_required": False,
                "source": (
                    f"{DISPOSITIONS_REL.as_posix()}"
                    f"#decision_state/rows_agent_recommended/#{index}"
                ),
            }
        )
    return out


def _qualified_interpretation_rows(
    dispositions: Mapping[str, Any], esr: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Rows confirmed on their disposition that still carry a deferral.

    Computed as the intersection, so the pair is the records' and not this
    module's. The decision_state statement says the same in prose.
    """
    deferrals = _deferral_index(dispositions)
    rows = _row_index(dispositions)
    confirmed = dispositions["decision_state"]["rows_operator_confirmed"]
    out: list[dict[str, Any]] = []
    for observation_id in confirmed:
        if observation_id not in deferrals:
            continue
        index, entry = deferrals[observation_id]
        row = rows[observation_id]
        decisions = ", ".join(row.get("operator_decision_ids") or ()) or "the approval"
        out.append(
            {
                "id": f"QI-{observation_id}",
                "kind": "qualified_interpretation",
                "observation_ids": (observation_id,),
                "subject": _one_line(
                    f"{observation_id} ({_esr_kind(esr, observation_id)}) is confirmed on its "
                    f"disposition by {decisions}, and an original-dependent question stays open. "
                    "The settled disposition does not settle the interpretation."
                ),
                "owner": "the private operator",
                "closure_evidence": _closure_from_deferral(entry),
                "original_required": True,
                "source": f"{DISPOSITIONS_REL.as_posix()}#open_operator_decisions/#{index}",
            }
        )
    return out


def _validation_case_rows(dispositions: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, case in enumerate(dispositions["assessor_validation_cases"]):
        limit = str(case["limit"])
        out.append(
            {
                "id": str(case["id"]),
                "kind": "assessor_validation_case",
                "observation_ids": tuple(case["observation_ids"]),
                "subject": _one_line(
                    f"{case['id']} is kept for the next assessor run, not acted on. "
                    f"{case['case']}"
                ),
                "owner": "the private operator",
                "closure_evidence": _one_line(
                    "The case re-read against a new assessor reading, with the recorded limit "
                    f"carried: {limit}"
                ),
                # Read off the recorded limit: a case whose own limit names
                # original-dependent evidence cannot be settled from this copy.
                "original_required": "original-dependent" in limit,
                "source": f"{DISPOSITIONS_REL.as_posix()}#assessor_validation_cases/#{index}",
            }
        )
    return out


def _unresolved_rows(
    dispositions: Mapping[str, Any], esr: Mapping[str, Any]
) -> list[dict[str, Any]]:
    deferrals = _deferral_index(dispositions)
    out: list[dict[str, Any]] = []
    for index, row in enumerate(dispositions["rows"]):
        if row.get("declared_status") != "Unresolved":
            continue
        observation_id = str(row["observation_id"])
        entry = deferrals.get(observation_id, (None, {}))[1]
        closure = (
            _closure_from_deferral(entry)
            if entry
            else "nothing further: the row names no deferred evidence of its own."
        )
        out.append(
            {
                "id": f"UNR-{observation_id}",
                "kind": "unresolved_disposition",
                "observation_ids": (observation_id,),
                "subject": _one_line(
                    f"{observation_id} ({_esr_kind(esr, observation_id)}) is declared "
                    "Unresolved. Its row states the readings that remain open and the operator "
                    "has chosen none, so none may be carried forward as the disposition."
                ),
                "owner": "the private operator",
                "closure_evidence": _one_line(
                    f"The operator's choice between the readings the row records, plus {closure}"
                ),
                "original_required": True,
                "source": f"{DISPOSITIONS_REL.as_posix()}#rows/#{index}",
            }
        )
    return out


def _deferred_question_rows(
    approval_text: str, known: frozenset[str]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, row in enumerate(_deferred_table(approval_text), start=1):
        out.append(
            {
                "id": f"DQ-{index:02d}",
                "kind": "deferred_question",
                "observation_ids": _normalised_observations(row["observations"], known),
                "subject": _one_line(
                    f"The approval explicitly defers the original-dependent decision on "
                    f"{row['observations']}. Its current review disposition is: "
                    f"{row['disposition']}"
                ),
                "owner": "the private operator",
                "closure_evidence": _one_line(row["evidence"]),
                "original_required": True,
                "source": f"{APPROVAL_REL.as_posix()}#{row['observations']}",
            }
        )
    return out


def _ticket_criterion_row(ledger_text: str) -> dict[str, Any]:
    line = _r04_criterion_line(ledger_text)
    return {
        "id": "TC-R04-05",
        "kind": "ticket_criterion",
        "observation_ids": (),
        "subject": _one_line(f"R04 acceptance criterion 5 is unchecked: {line}"),
        "owner": "the operator",
        "closure_evidence": _one_line(
            "Adoption of a declaration into an active register, once D13's deferral lifts, "
            "followed by a regeneration exercise over the adopted register with the new "
            "register hash and the affected bindings recorded. Adopting an original-fidelity "
            "claim additionally needs the original; adopting an extraction-fidelity claim "
            "does not, which is why this row does not require it."
        ),
        "original_required": False,
        "precondition": R04_PRECONDITION,
        "source": f"{LEDGER_REL.as_posix()}#{R04_CRITERION}",
    }


# --------------------------------------------------------------------------- #
# The statements the register has to carry
# --------------------------------------------------------------------------- #


def _statements(
    revisions: Mapping[str, Any],
    esr: Mapping[str, Any],
    audits: Mapping[str, int],
    candidate_hash: str,
    document_id: str,
) -> list[dict[str, Any]]:
    """The two statements a reader needs in order to not misread the numbers.

    Both are measured against bound records. The arithmetic in each claim is
    recomputed here, so a record whose figures move makes this module refuse
    rather than print a stale sentence.
    """
    open_rows = revisions["open"]
    closed_rows = revisions["closed"]
    if closed_rows:
        raise DeferralAuthoringError(
            f"{REVISIONS_REL}: {len(closed_rows)} revision rows are closed; the statement that "
            "every criticism has open revision work no longer holds"
        )
    observations = esr["observations"]
    criticisms = {
        o["id"]: o["kind"] for o in observations if o.get("kind") != "strength"
    }
    shortcomings = sum(1 for kind in criticisms.values() if kind == "shortcoming")
    minor = sum(1 for kind in criticisms.values() if kind == "minor_shortcoming")
    if shortcomings + minor != len(criticisms):
        raise DeferralAuthoringError(
            f"{ESR_REL}: the criticisms carry a kind beyond shortcoming and minor_shortcoming"
        )
    planned = {str(r["observation_id"]) for r in open_rows}
    if planned != set(criticisms):
        raise DeferralAuthoringError(
            f"{REVISIONS_REL}: the open revision rows are not the criticisms of {ESR_REL}; "
            f"{sorted(planned ^ set(criticisms))} differ"
        )
    first, middle, last = (
        audits[AUDIT_R03_REL.as_posix()],
        audits[AUDIT_R04_REL.as_posix()],
        audits[AUDIT_APPROVED_REL.as_posix()],
    )
    retired = first - last
    readings = (
        ("the reading before R03", AUDIT_R03_REL, first),
        ("the reading after R03", AUDIT_R04_REL, middle),
        ("the approved reading", AUDIT_APPROVED_REL, last),
    )
    s1: list[dict[str, Any]] = []
    for label, rel, total in readings:
        s1.append(
            {
                "id": f"S1-M{len(s1) + 1}",
                "claim": f"{label} records {total} findings",
                "record": rel.as_posix(),
                "field": "findings_total",
                "expected": total,
            }
        )
    for label, rel, _total in readings:
        s1.append(
            {
                "id": f"S1-M{len(s1) + 1}",
                "claim": f"{label} is of the same candidate bytes",
                "record": rel.as_posix(),
                "field": "candidate_hash",
                "expected": candidate_hash,
            }
        )
        s1.append(
            {
                "id": f"S1-M{len(s1) + 1}",
                "claim": f"{label} is of the same document",
                "record": rel.as_posix(),
                "field": "document_id",
                "expected": document_id,
            }
        )

    return [
        {
            "id": "S1",
            "claim": _one_line(
                f"The integrity audit's recorded {first} to {middle} to {last} finding sequence "
                "is three readings of one unchanged candidate. All three carry the same "
                "candidate hash and the same document id, so the fall reflects changed "
                "interpretation and changed audit rules — operator decision D11 and ticket R03 "
                f"retired {retired} findings as rules, not as repairs. It is not "
                f"{retired} repaired proposal defects, and no proposal text changed between the "
                "three readings."
            ),
            "measurements": s1,
        },
        {
            "id": "S2",
            "claim": _one_line(
                f"All {len(criticisms)} evaluation-summary criticisms still have open revision "
                f"work — the record's {shortcomings} shortcomings and {minor} minor "
                "shortcomings. The approved revision plan carries every one of them as open and "
                "closes none. Retiring an audit finding retired an audit rule, and changed "
                "nothing an evaluation-summary criticism names."
            ),
            "measurements": [
                {
                    "id": "S2-M1",
                    "claim": f"{len(open_rows)} criticisms carry open revision work",
                    "record": REVISIONS_REL.as_posix(),
                    "field": "open",
                    "expected_length": len(open_rows),
                },
                {
                    "id": "S2-M2",
                    "claim": (
                        f"the evaluation summary records {len(observations)} observations, of "
                        f"which these {len(criticisms)} are the criticisms"
                    ),
                    "record": ESR_REL.as_posix(),
                    "field": "observations",
                    "expected_length": len(observations),
                },
                {
                    "id": "S2-M3",
                    "claim": "none is closed",
                    "record": REVISIONS_REL.as_posix(),
                    "field": "closed",
                    "expected_length": 0,
                },
            ],
        },
    ]


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

#: Every record the register binds, with its role and what it holds.
BOUND_RECORDS: tuple[tuple[Path, str, str], ...] = (
    (
        APPROVAL_REL,
        "immutable_evidence",
        "the operator approval of 2026-10-08, its fifteen decisions and its "
        "original-dependent deferred table",
    ),
    (
        DISPOSITIONS_REL,
        "immutable_evidence",
        "the approved dispositions: the review status of all 29 observations, the twelve "
        "deferred decisions, and the two assessor validation cases",
    ),
    (
        REVISIONS_REL,
        "immutable_evidence",
        "the approved revision plan, which carries the open revision work per criticism",
    ),
    (ESR_REL, "immutable_evidence", "the evaluation summary this comparison is against"),
    (AUDIT_R03_REL, "immutable_evidence", "the integrity audit as it stood before R03"),
    (AUDIT_R04_REL, "immutable_evidence", "the integrity audit after R03's two rule corrections"),
    (
        AUDIT_APPROVED_REL,
        "immutable_evidence",
        "the integrity audit the approved dispositions cite, after D11 retired the "
        "undeclared-dependency rule",
    ),
    (
        LEDGER_REL,
        "tracked_input",
        "the predecessor ticket ledger, which carries the unchecked R04 criterion",
    ),
)


def render_register(repo_root: Path) -> dict[str, Any]:
    """The register, derived from the eight records it binds.

    Refuses rather than renders a stale claim: the three readings must still
    share a candidate and a document, the ledger's R04 box must still be
    unchecked, and the revision plan must still carry every criticism open.
    """
    approval_text = (repo_root / APPROVAL_REL).read_text(encoding="utf-8-sig")
    ledger_text = (repo_root / LEDGER_REL).read_text(encoding="utf-8-sig")
    dispositions = _read_json(repo_root / DISPOSITIONS_REL)
    revisions = _read_json(repo_root / REVISIONS_REL)
    esr = _read_json(repo_root / ESR_REL)

    audits: dict[str, int] = {}
    candidate_hashes: set[str] = set()
    document_ids: set[str] = set()
    for rel in (AUDIT_R03_REL, AUDIT_R04_REL, AUDIT_APPROVED_REL):
        record = _read_json(repo_root / rel)
        audits[rel.as_posix()] = int(record["findings_total"])
        candidate_hashes.add(str(record["candidate_hash"]))
        document_ids.add(str(record["document_id"]))
    if len(candidate_hashes) != 1 or len(document_ids) != 1:
        raise DeferralAuthoringError(
            "the three audits do not share a candidate hash and a document id; the statement "
            "that the finding sequence is three readings of one candidate no longer holds"
        )

    candidate_hash = candidate_hashes.pop()
    document_id = document_ids.pop()

    rows: list[dict[str, Any]] = [_ticket_criterion_row(ledger_text)]
    rows += _operator_decision_rows(dispositions, esr)
    rows += _agent_recommendation_rows(dispositions, esr)
    rows += _qualified_interpretation_rows(dispositions, esr)
    rows += _validation_case_rows(dispositions)
    rows += _unresolved_rows(dispositions, esr)
    rows += _deferred_question_rows(approval_text, _esr_ids(esr))
    for row in rows:
        row["state"] = "open"

    sources = [
        {
            "path": rel.as_posix(),
            "sha256": file_sha256(repo_root / rel),
            "role": role,
            "holds": holds,
        }
        for rel, role, holds in BOUND_RECORDS
    ]

    return {
        "schema": SCHEMA,
        "record_type": "open_deferral_register",
        "register_name": "open_deferrals_2026-10-12",
        "subject": (
            f"{dispositions['candidate'].rsplit('/', 1)[-1]}, under the operator approval of "
            "2026-10-08"
        ),
        "authored_on": AUTHORED_ON,
        "ticket": TICKET,
        "advisory": True,
        "blocking": False,
        "purpose": (
            "Every item the operator approval of 2026-10-08 left open, in one place, so that a "
            "milestone accepting that package cannot inherit a deferral as settled. Each row "
            "names what is open, who closes it, the evidence that would close it, and whether "
            "that evidence requires the submitted original. No row closes without its evidence: "
            "harness.deferral_register.check fails the register if one does."
        ),
        "review_state": "agent_drafted_pending_operator_review",
        "declared_status": "Inferred",
        "declared_status_note": (
            "Inferred, not Confirmed. Each row's existence is read off a committed record, which "
            "is evidence. That a row is still open is an inference from the absence of a closing "
            "decision, and an absence is not a confirmation. The operator's own review is what "
            "would move this."
        ),
        "supersedes": (
            "nothing. This is the first register of the deferrals of the operator approval of "
            "2026-10-08. The records it binds are its predecessors in evidence, not in version: "
            "the approved dispositions supersede the R05 record, and this register reads the "
            "approved one. A correction to this register is a successor register, never an edit."
        ),
        "uncertainties": [
            "The ticket ledger is bound as a tracked input, so any edit to it - including one "
            "unrelated to the R04 criterion - makes this register stale until it is re-derived.",
            "The R04 row closes on adoption into an active register once D13's deferral lifts, "
            "which is a decision this repository cannot make.",
            "No row has ever been closed, so the closure path is covered by synthetic cases "
            "only.",
            "Several rows name one observation on purpose. ESR-E-04 carries three and ESR-Q-01 "
            "three. The cross-reference is what keeps them from being counted as separate items.",
            "DQ-08's subject, the M7.3 milestone and the appointment windows, is not an "
            "evaluation summary observation, so it joins the ticket criterion as a row naming "
            "none.",
        ],
        "authority_note": (
            "This register is a successor artifact. It confers no authority, closes no row and "
            "edits none of the records it binds. An operator approval is an authority fact; "
            "Confirmed, Inferred, Assumed and Unresolved describe evidence, and approving the "
            "package that contains a deferral does not resolve the deferral."
        ),
        "written_by": "tools/author_deferral_register.py",
        "sources": sources,
        "statements": _statements(
            revisions, esr, audits, candidate_hash, document_id
        ),
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# Checking and writing
# --------------------------------------------------------------------------- #


def render_all(repo_root: Path) -> dict[str, bytes]:
    """The one artifact this module writes, by relative path."""
    return {REGISTER_REL.as_posix(): canonical_json_bytes(render_register(repo_root))}


def check(repo_root: Path) -> list[str]:
    """Relative paths whose bytes differ from the rendering, or are absent."""
    return [
        rel
        for rel, data in render_all(repo_root).items()
        if not (repo_root / rel).is_file() or (repo_root / rel).read_bytes() != data
    ]


def write(repo_root: Path) -> list[str]:
    changed: list[str] = []
    for rel, data in render_all(repo_root).items():
        target = repo_root / rel
        if target.is_file() and target.read_bytes() == data:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(data.decode("utf-8"), target)
        changed.append(rel)
    return changed


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the register would change")
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)
    repo_root = args.repo_root or find_repo_root()
    try:
        if args.check:
            stale = check(repo_root)
            for rel in stale:
                print(f"would change: {rel}")
            print("up to date" if not stale else f"{len(stale)} file(s) would change")
            return 1 if stale else 0
        changed = write(repo_root)
        for rel in changed:
            print(f"wrote: {rel}")
        print("no change" if not changed else f"{len(changed)} file(s) written")
        print(
            "now check it and render its reading:\n"
            f"  py -3.10 -m harness.commands.deferral_register --register {REGISTER_REL.as_posix()}"
        )
        return 0
    except DeferralAuthoringError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
