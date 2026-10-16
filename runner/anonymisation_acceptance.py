"""Operator acceptance of a derivative, stage A7 of the anonymisation pipeline (AN11).

AN11 of ``.scratch/msca-dn-anonymisation/tickets.md``, stage A7 of
``plans/msca_dn_anonymisation_handoff_2026-10-14.md``. Pure code, with no
model: :func:`accept` reads every stage record of a derivative, checks that
they describe this file under one policy and one stage chain, and writes two
records.

The private record
------------------
:data:`SCHEMA`. The full acceptance: every stage record bound by the hash of
its bytes, the mapping table's parts (the dictionary, the edit logs and the
Table 1.4.1 row map), the re-identification details by hash, and the
operator's input. It stays in the private network.

The public record
-----------------
:data:`PUBLIC_SCHEMA`, a decision record. Metadata only: the derivative's
hash, the policy's version and hash, the pipeline revision, the A5 and A6
counts by category, the model ids, the operator's signature and the private
environment's rule that permits the export. It is the record the J0 D3
condition points to (:data:`J0_RECORD_REL`). :func:`public_record` builds it
from the private record alone, so it can hold nothing the private record does
not.

It refuses to build unless the leak scan passed with no hit, the model attack
passed with no correct guess, A6 passed with no finding, A4 replaced Table
1.4.1 and the operator attested every read in :data:`ATTESTATIONS`. It is then
held to two checks before anything is written. Its keys are a closed set
(:func:`check_public_shape`), except the category ids of a tally, whose
leaves must be counts. Every string in it, keys included, is matched
against the entity dictionary with case folded, so an operator entry that
names an entity is refused, not exported.

What A7 requires of A3
----------------------
A3 (AN6) writes a plan and applies nothing, and A6 reads no A3 log. So a
plan holding a validated edit, or a proposed entity awaiting the operator,
is refused here: the derivative would not carry what A3 asked for. A plan
with neither shows that the rewrite ran and asked for nothing.

Declared limits
---------------
* **The signature is a declaration.** ``signed_by`` and ``signed_on`` are the
  operator's entries. Nothing here signs them cryptographically.
* **The export rule is the private environment's.** Runbook §10 leaves it to
  that environment, so this repository cannot check it. The public record
  carries the rule the operator names, declared ``Assumed``.
* **The pipeline revision is a declaration**, as in the AN10 register. No
  stage record carries the commit it ran from.
* **Inside the private network** is the operator's attestation. Every path
  this module reads or writes is refused inside this repository, which is
  all code can show.

The export itself is written down in :data:`EXPORT_PROCEDURE_REL`.

Constitutional standing: an authoring tool, not a runtime component. It
evaluates no gate, invokes no model and writes no Tier 5 artifact
(CLAUDE.md §13.10). No manifest node binds it. The public record is a Tier 4
decision record once the operator commits it.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from runner import anonymisation_attack as attack
from runner import anonymisation_fidelity as fidelity
from runner import anonymisation_intake as intake
from runner import anonymisation_leak_scan as scan_stage
from runner import anonymisation_matching as matching
from runner import anonymisation_redaction as redaction
from runner import anonymisation_rewrite as rewrite
from runner import anonymisation_table as table
from runner.anonymisation_policy import LoadedPolicy, require_hash
from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.model_ids import canonical_model_id

SCHEMA = "anonymisation_acceptance/1"
RECORD_TYPE = "anonymisation_acceptance"
PUBLIC_SCHEMA = "anonymisation_acceptance_public/1"
INPUT_SCHEMA = "anonymisation_acceptance_input/1"
INPUT_RECORD_TYPE = "anonymisation_acceptance_input"

PRIVATE_FILE = "acceptance.json"
PUBLIC_FILE = "public_acceptance.json"

J0_RECORD_ID = "harness-jev-j0-governance_2026-10-14"
J0_RECORD_REL = f"docs/tier4_orchestration_state/decision_log/{J0_RECORD_ID}.json"
EXPORT_PROCEDURE_REL = "plans/msca_dn_anonymisation_export_procedure.md"

#: What the operator attests before signing, each of which must be true.
ATTESTATIONS: tuple[str, ...] = (
    "derivative_read",
    "leak_scan_report_read",
    "leak_scan_review_items_read",
    "reidentification_report_read",
    "structural_fidelity_report_read",
    "ran_inside_private_network",
)

#: The parts of the J0 D3 condition, in the order the J0 record states them.
D3_CONDITION_PARTS: tuple[str, ...] = (
    "redaction_and_rewrite_ran",
    "ran_inside_private_network",
    "reidentification_found_no_hit",
    "operator_signed",
    "table_1_4_1_replaced",
    "export_permitted_by_private_rule",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EXPORT_RULE_FIELDS = ("rule_id", "issued_by", "read_on")


class AcceptanceRefused(RuntimeError):
    """The derivative cannot be accepted as asked. Nothing was written."""


@dataclass(frozen=True)
class AcceptanceResult:
    private_record: Path
    public_record: Path
    public: dict[str, Any]


@dataclass(frozen=True)
class _Bound:
    """A record read from a private path, with the hash of its bytes."""

    name: str
    record: dict[str, Any]
    sha256: str

    def binding(self) -> dict[str, str]:
        return {"file": self.name, "sha256": self.sha256}


def _read(path: Path, what: str) -> _Bound:
    path = intake.require_private(path, what)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise AcceptanceRefused(
            f"{what} cannot be read ({type(exc).__name__}). Nothing was written."
        ) from exc
    try:
        record = json.loads(data)
    except ValueError as exc:
        raise AcceptanceRefused(f"{what} is not valid JSON. Nothing was written.") from exc
    if not isinstance(record, dict):
        raise AcceptanceRefused(f"{what} must hold a JSON object. Nothing was written.")
    return _Bound(path.name, record, hashlib.sha256(data).hexdigest())


def _field(record: Mapping[str, Any], what: str, *keys: str) -> Any:
    value: Any = record
    for key in keys:
        if not isinstance(value, Mapping) or key not in value:
            raise AcceptanceRefused(f"{what} carries no {'.'.join(keys)}")
        value = value[key]
    return value


def _require_schema(bound: _Bound, schema: str, what: str) -> None:
    if bound.record.get("schema") != schema:
        raise AcceptanceRefused(f"{what} is not a {schema} record")


def _require_same(value: Any, expected: str, what: str, of: str) -> None:
    if value != expected:
        raise AcceptanceRefused(
            f"{what} is of {of} {value}, not {expected}. Every record an acceptance binds "
            f"describes the one derivative being accepted, under the one policy."
        )


# --------------------------------------------------------------------------- #
# The stage records
# --------------------------------------------------------------------------- #


def _stage_chain(
    report: _Bound, logs: Sequence[_Bound]
) -> list[dict[str, str]]:
    links = _field(report.record, "the structural fidelity report", "input", "stage_logs")
    if not isinstance(links, list) or len(links) != len(logs):
        raise AcceptanceRefused(
            f"{len(logs)} stage log(s) were given and the structural fidelity report bound "
            f"{len(links) if isinstance(links, list) else 'none'}. An acceptance binds the "
            f"chain A6 checked, every link of it."
        )
    out: list[dict[str, str]] = []
    for link, log in zip(links, logs):
        if not isinstance(link, Mapping) or log.sha256 != link.get("log_sha256"):
            raise AcceptanceRefused(
                f"the stage log {log.name} is not the one the structural fidelity report bound "
                f"at that link: its bytes hash to another value"
            )
        out.append({"stage": str(link.get("stage")), "file": log.name, "sha256": log.sha256,
                    "output_sha256": str(link.get("output_sha256"))})
    return out


def _table_log(logs: Sequence[_Bound]) -> _Bound:
    tables = [log for log in logs if log.record.get("schema") == table.SCHEMA]
    if not tables:
        raise AcceptanceRefused(
            "no A4 table synthesis log is in the stage chain. The J0 D3 condition requires "
            "Table 1.4.1 replaced by a synthetic table, and a derivative without one is not "
            "accepted."
        )
    return tables[-1]


def _redaction_log(logs: Sequence[_Bound]) -> _Bound:
    if not logs or logs[0].record.get("schema") != redaction.SCHEMA:
        raise AcceptanceRefused(
            "the stage chain does not start with an A2 redaction log. The J0 D3 condition "
            "requires the deterministic redaction to have run."
        )
    return logs[0]


def _rewrite(plan: _Bound, a2_output: str, report: _Bound, policy_sha256: str) -> dict[str, Any]:
    _require_schema(plan, rewrite.SCHEMA, "the rewrite plan")
    _require_same(_field(plan.record, "the rewrite plan", "input", "derivative_sha256"),
                  a2_output, "the rewrite plan", "the A2 output")
    _require_same(plan.record.get("policy_sha256"), policy_sha256, "the rewrite plan",
                  "the policy")
    a3_input = _field(report.record, "the re-identification report", "input", "a3_input_sha256")
    _require_same(a3_input, a2_output, "the re-identification report's A3 input",
                  "the A2 output")
    model_id = _field(plan.record, "the rewrite plan", "model", "model_id")
    named = _field(report.record, "the re-identification report", "model", "a3_model_id")
    # The attack's own independence guard compares canonical ids (AN1c); so does this one.
    if not (isinstance(model_id, str) and isinstance(named, str)
            and canonical_model_id(model_id) == canonical_model_id(named)):
        raise AcceptanceRefused(
            f"the rewrite plan was made by A3 model {model_id!r}, and the re-identification "
            f"report checked independence against {named!r}. The attack must not share the "
            f"rewriter's model, so the two must name the same A3 model."
        )
    passages = plan.record.get("passages")
    if not (isinstance(passages, list) and all(isinstance(p, Mapping) for p in passages)):
        raise AcceptanceRefused("the rewrite plan carries no list of passages")
    malformed = sum(1 for p in passages if p.get("response_status") != "valid")
    edits = sum(len(p.get("edits") or []) for p in passages)
    proposals = sum(int(p.get("proposals") or 0) for p in passages)
    if malformed:
        raise AcceptanceRefused(
            f"the rewrite plan holds {malformed} malformed reply(ies). A3 did not finish, so "
            f"the rewrite cannot be said to have run."
        )
    if edits:
        raise AcceptanceRefused(
            f"the rewrite plan holds {edits} validated edit(s) that no stage applied: A3 "
            f"applies none, and A6 reads no A3 log. The derivative does not carry what A3 asked "
            f"for, so it is not accepted."
        )
    if proposals:
        raise AcceptanceRefused(
            f"the rewrite plan queues {proposals} proposed entity(ies) for the operator. Add "
            f"the approved ones to the dictionary and re-run from A2 before acceptance."
        )
    return {"model_id": model_id, "passages_sent": len(passages), "edits_proposed": edits,
            "entities_proposed": proposals, "applied": False}


def _operator(bound: _Bound, derivative_sha256: str) -> dict[str, Any]:
    record = bound.record
    if record.get("schema") != INPUT_SCHEMA or record.get("record_type") != INPUT_RECORD_TYPE:
        raise AcceptanceRefused(f"the operator's input is not a {INPUT_SCHEMA} record")
    if record.get("derivative_sha256") != derivative_sha256:
        raise AcceptanceRefused(
            "the operator's input accepts another derivative. A signature covers the file "
            "the operator read."
        )
    if record.get("decision") != "accept":
        raise AcceptanceRefused(
            f"the operator's decision is {record.get('decision')!r}, not 'accept'"
        )
    revision = record.get("pipeline_revision")
    if not (isinstance(revision, str) and _COMMIT.match(revision)):
        raise AcceptanceRefused(
            "the operator's pipeline_revision is not a 40-digit commit id. Name the commit "
            "the stages ran from, not a branch or a short id."
        )
    for key in ("signed_by", "signed_on"):
        if not (isinstance(record.get(key), str) and record[key].strip()):
            raise AcceptanceRefused(f"the operator's input carries no {key}")
    if not _DATE.match(record["signed_on"]):
        raise AcceptanceRefused("the operator's signed_on is not an ISO date (YYYY-MM-DD)")
    rule = record.get("export_rule")
    if not (isinstance(rule, Mapping) and set(rule) == set(_EXPORT_RULE_FIELDS)
            and all(isinstance(rule[k], str) and rule[k].strip() for k in _EXPORT_RULE_FIELDS)):
        raise AcceptanceRefused(
            f"the operator's export_rule must name {', '.join(_EXPORT_RULE_FIELDS)}: the private "
            f"environment's rule that permits the export (runbook §10)"
        )
    if not _DATE.match(rule["read_on"]):
        raise AcceptanceRefused("the operator's export_rule.read_on is not an ISO date")
    attestations = record.get("attestations")
    if not (isinstance(attestations, Mapping) and set(attestations) == set(ATTESTATIONS)):
        raise AcceptanceRefused(
            f"the operator's attestations must be exactly {', '.join(ATTESTATIONS)}"
        )
    return {
        "decision": "accept",
        "signed_by": record["signed_by"],
        "signed_on": record["signed_on"],
        "pipeline_revision": revision,
        "attestations": {name: attestations[name] for name in ATTESTATIONS},
        "export_rule": {k: rule[k] for k in _EXPORT_RULE_FIELDS},
        "input_sha256": bound.sha256,
    }


def _attack_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    targets = report.get("targets")
    if not (isinstance(targets, list) and all(isinstance(t, Mapping) for t in targets)):
        raise AcceptanceRefused("the re-identification report carries no list of targets")
    return {
        "verdict": report.get("verdict"),
        "by_category": report.get("by_category"),
        "targets": [
            {"target": t.get("target"), "category": t.get("category"),
             "guess_admissible": t.get("guess_admissible"), "counts": t.get("counts"),
             "failed": t.get("failed")}
            for t in targets
        ],
        "correct_unlocated": report.get("correct_unlocated"),
        "passages_sent_back": report.get("passages_sent_back"),
        "malformed_guesses": report.get("malformed_guesses"),
        "review_rule_status": report.get("review_rule_status"),
        "limit": report.get("limit"),
    }


# --------------------------------------------------------------------------- #
# The public record
# --------------------------------------------------------------------------- #


def _refuse_unless_passed(private: Mapping[str, Any]) -> None:
    """The conditions without which no public record is built.

    A summary of the wrong shape is refused, not let through as another error.
    """
    try:
        _check_passed(private)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise AcceptanceRefused(
            f"the private record's stage summaries are malformed ({type(exc).__name__}), so "
            f"whether A5 and A6 passed cannot be read. Nothing was written."
        ) from exc


def _check_passed(private: Mapping[str, Any]) -> None:
    scan =_field(private, "the private record", "reidentification", "leak_scan")
    hits = _field(scan, "the leak scan summary", "counts", "hits")
    if scan.get("verdict") != "pass" or any(int(n) for n in hits.values()):
        raise AcceptanceRefused(
            f"the leak scan did not pass (verdict {scan.get('verdict')!r}, "
            f"{sum(int(n) for n in hits.values())} hit(s)). Any hit fails the derivative; fix "
            f"A2 and re-run."
        )
    model = _field(private, "the private record", "reidentification", "model_attack")
    if model.get("verdict") != "passed":
        raise AcceptanceRefused(
            f"the model attack did not pass (verdict {model.get('verdict')!r}). A failed "
            f"target goes back to A3; a malformed reply means the attack did not finish."
        )
    correct = sum(int((t.get("counts") or {}).get("correct", 0)) for t in model["targets"]
                  if not t.get("guess_admissible"))
    correct += int(model.get("correct_unlocated") or 0)
    if correct:
        raise AcceptanceRefused(
            f"the model attack made {correct} correct guess(es) at a target the policy does "
            f"not keep. The J0 D3 condition is that re-identification found no hit, whatever "
            f"threshold the policy sets."
        )
    fid = _field(private, "the private record", "structural_fidelity")
    findings = sum(int(c.get("findings", 0)) for c in (fid.get("counts") or {}).values())
    if fid.get("verdict") != "pass" or findings:
        raise AcceptanceRefused(
            f"the structural fidelity comparison did not pass (verdict {fid.get('verdict')!r}, "
            f"{findings} finding(s)). Every difference must be explained by the policy before "
            f"acceptance."
        )
    if _field(private, "the private record", "table_1_4_1", "synthetic") is not True:
        raise AcceptanceRefused(
            "Table 1.4.1 is not replaced by a synthetic table, which the J0 D3 condition "
            "requires"
        )
    attestations = _field(private, "the private record", "operator", "attestations")
    unread = [name for name in ATTESTATIONS if attestations.get(name) is not True]
    if unread:
        raise AcceptanceRefused(
            f"the operator did not attest {', '.join(unread)}. The operator's own read is the "
            f"last line of the re-identification check."
        )


def _d3_parts(private: Mapping[str, Any]) -> list[dict[str, str]]:
    bases = {
        "redaction_and_rewrite_ran": (
            "Confirmed",
            "The A2 redaction log opens the stage chain the A6 report bound, and the A3 rewrite "
            "plan of the A2 output is bound by hash, with no edit or entity left unapplied.",
        ),
        "ran_inside_private_network": (
            "Assumed",
            "The operator attests it. Every stage, and this acceptance, refused any path inside "
            "the repository, which is all code can show.",
        ),
        "reidentification_found_no_hit": (
            "Confirmed",
            "The A5 leak scan passed with no hit, and the A5 model attack passed with no "
            "correct guess at a target the policy does not keep.",
        ),
        "operator_signed": (
            "Assumed",
            "The operator's input names the signer and the date, and attests each read. The "
            "signature is a declaration, not a cryptographic one.",
        ),
        "table_1_4_1_replaced": (
            "Confirmed",
            "An A4 table synthesis log is in the stage chain the A6 report bound, and A6 passed.",
        ),
        "export_permitted_by_private_rule": (
            "Assumed",
            "The operator names the private environment's rule. Runbook section 10 leaves that "
            "rule to the environment, so this repository cannot check it.",
        ),
    }
    return [{"part": part, "declared_status": bases[part][0], "basis": bases[part][1]}
            for part in D3_CONDITION_PARTS]


#: A tally: category ids mapped to counts, or to further tallies. Its keys are
#: not fixed, so they are held to the dictionary check; its leaves are integers.
_TALLY = "tally"


def _list_of(spec: Any) -> tuple[str, Any]:
    return ("list", spec)


_PUBLIC_KEYS: dict[str, Any] = {
    "schema": None, "record_type": None, "id": None, "date": None, "stage": None,
    "ticket": None, "authority": None, "review_state": None, "decision": None,
    "derivative": {"sha256": None, "bytes": None},
    "policy": {"policy_id": None, "policy_version": None, "sha256": None},
    "pipeline_revision": {"commit": None, "declared_status": None, "basis": None},
    "a5_reidentification": {
        "leak_scan": {"verdict": None, "counts": _TALLY, "report_sha256": None},
        "model_attack": {
            "verdict": None, "by_category": _TALLY,
            "targets": _list_of({"target": None, "category": None, "guess_admissible": None,
                                 "counts": _TALLY, "failed": None}),
            "correct_unlocated": None, "passages_sent_back": None, "malformed_guesses": None,
            "review_rule_status": None, "limit": None, "report_sha256": None,
        },
    },
    "a6_structural_fidelity": {"verdict": None, "counts": _TALLY, "report_sha256": None},
    "table_1_4_1": {"synthetic": None, "data_rows": None, "columns": None},
    "models": {"a3": {"model_id": None, "canonical_model_id": None},
               "a5": {"model_id": None, "canonical_model_id": None}},
    "operator_signature": {"signed_by": None, "signed_on": None,
                           "attestations": {name: None for name in ATTESTATIONS},
                           "basis": None},
    "export_rule": {"rule_id": None, "issued_by": None, "read_on": None,
                    "declared_status": None, "basis": None},
    "export_procedure": None,
    "d3_condition": {"record": None, "class": None,
                     "parts": _list_of({"part": None, "declared_status": None, "basis": None})},
    "private_record_sha256": None,
    "not_evidence_of": _list_of(None),
    "privacy": None,
}

_SCALARS = (str, int, float, bool, type(None))


def _refuse_shape(where: str, why: str) -> None:
    raise AcceptanceRefused(
        f"the public record's {where or 'top level'} {why}. It carries metadata only, by a "
        f"closed set of keys."
    )


def _shape(value: Any, spec: Any, where: str) -> None:
    if spec is None:
        if not isinstance(value, _SCALARS):
            _refuse_shape(where, "must be a single value")
        return
    if spec == _TALLY:
        if not isinstance(value, Mapping):
            _refuse_shape(where, "must be a tally")
        for key, sub in value.items():
            if not (isinstance(sub, Mapping) or (isinstance(sub, int)
                                                 and not isinstance(sub, bool))):
                _refuse_shape(f"{where}.{key}", "must be a count")
            if isinstance(sub, Mapping):
                _shape(sub, _TALLY, f"{where}.{key}")
        return
    if isinstance(spec, tuple):
        if not isinstance(value, list):
            _refuse_shape(where, "must be a list")
        for n, item in enumerate(value):
            _shape(item, spec[1], f"{where}[{n}]")
        return
    if not isinstance(value, Mapping) or set(value) != set(spec):
        extra = sorted(set(value) - set(spec)) if isinstance(value, Mapping) else []
        missing = sorted(set(spec) - set(value)) if isinstance(value, Mapping) else []
        _refuse_shape(where, f"does not have its declared keys (extra {extra}, missing "
                             f"{missing})")
    for key, sub in spec.items():
        _shape(value[key], sub, f"{where}.{key}" if where else key)


def check_public_shape(record: Mapping[str, Any]) -> None:
    """Refuse *record* unless its keys are exactly the public record's declared keys."""
    _shape(record, _PUBLIC_KEYS, "")


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [s for k, v in value.items() for s in (str(k), *_strings(v))]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


#: A sha256 digest or a git revision, whole. A digest is one-way, so it holds no
#: private content, but its hex digits can read as an identifier: nine decimal
#: digits in a row match the grant number pattern (found by AN12).
_DIGEST = re.compile(r"^(?:[0-9a-f]{64}|[0-9a-f]{40})$")


def is_digest(value: str) -> bool:
    """Whether *value* is a whole lowercase sha256 digest or 40-hex revision."""
    return bool(_DIGEST.match(value))


def _refuse_entities(record: Mapping[str, Any], entities: matching.EntityDictionary) -> None:
    """Refuse *record* if any string in it matches the dictionary, case folded.

    A whole digest is not scanned: see :data:`_DIGEST`.
    """
    folded = dataclasses.replace(
        entities,
        entries=tuple(dataclasses.replace(e, match_case=False) for e in entities.entries),
    )
    found: list[tuple[str, Optional[str]]] = []
    for string in _strings(record):
        if is_digest(string):
            continue
        for dictionary in (entities, folded):
            found += [(m.category, m.entry_id or m.regex_class)
                      for m in matching.find_matches(string, dictionary)]
    if found:
        named = sorted({f"{cat}:{eid}" for cat, eid in found})
        raise AcceptanceRefused(
            f"the public record matches the entity dictionary ({', '.join(named)}). It may hold "
            f"no private content; correct the operator's entries. Nothing was written."
        )


def public_record(
    private: Mapping[str, Any], *, private_sha256: str, entities: matching.EntityDictionary
) -> dict[str, Any]:
    """The public metadata record of the acceptance *private*. Pure.

    Refuses unless A5 and A6 passed, Table 1.4.1 was replaced and the operator
    attested every read; then refuses a record that does not have its declared
    keys or that matches the dictionary *entities*.
    """
    _refuse_unless_passed(private)
    operator = private["operator"]
    derivative = private["derivative"]
    reid = private["reidentification"]
    signed_on = operator["signed_on"]
    record = {
        "schema": PUBLIC_SCHEMA,
        "record_type": "decision_record",
        "id": f"anonymisation-acceptance-{derivative['sha256'][:12]}_{signed_on}",
        "date": signed_on,
        "stage": "A7",
        "ticket": "AN11 of .scratch/msca-dn-anonymisation/tickets.md builds this record; AN13 "
                  "signs it",
        "authority": "The operator's acceptance of an anonymised derivative, signed in the "
                     "private network. Advisory, out-of-band. It adds no runtime gate and amends "
                     "no constitutional rule.",
        "review_state": "operator_signed",
        "decision": "The derivative whose hash is recorded here is accepted as data class D3 of "
                    "the J0 record, and may be exported through the written procedure.",
        "derivative": {"sha256": derivative["sha256"], "bytes": derivative["bytes"]},
        "policy": dict(private["policy"]),
        "pipeline_revision": {
            "commit": operator["pipeline_revision"],
            "declared_status": "Assumed",
            "basis": "The operator's declaration. No stage record carries the commit it ran "
                     "from.",
        },
        "a5_reidentification": {
            "leak_scan": {"verdict": reid["leak_scan"]["verdict"],
                          "counts": reid["leak_scan"]["counts"],
                          "report_sha256": private["records"]["leak_scan"]["sha256"]},
            "model_attack": {**reid["model_attack"],
                             "report_sha256":
                                 private["records"]["reidentification_report"]["sha256"]},
        },
        "a6_structural_fidelity": {
            "verdict": private["structural_fidelity"]["verdict"],
            "counts": private["structural_fidelity"]["counts"],
            "report_sha256": private["records"]["structural_fidelity"]["sha256"],
        },
        "table_1_4_1": dict(private["table_1_4_1"]),
        "models": private["models"],
        "operator_signature": {
            "signed_by": operator["signed_by"],
            "signed_on": signed_on,
            "attestations": operator["attestations"],
            "basis": "A declaration in the operator's private input, bound by hash in the "
                     "private record.",
        },
        "export_rule": {
            **operator["export_rule"],
            "declared_status": "Assumed",
            "basis": "Named by the operator. Runbook section 10 leaves the rule to the private "
                     "environment, and this repository does not hold it.",
        },
        "export_procedure": EXPORT_PROCEDURE_REL,
        "d3_condition": {"record": J0_RECORD_ID, "class": "D3", "parts": _d3_parts(private)},
        "private_record_sha256": private_sha256,
        "not_evidence_of": [
            "that a motivated human expert in the field could not re-identify the derivative",
            "that any score on the derivative is informative about the original (A8 measures "
            "that)",
            "that the vendor's zero data retention is confirmed, which the J0 record requires "
            "separately before anything goes to Jev",
        ],
        "privacy": "Metadata only: hashes, counts, categories, model ids, dates and the "
                   "operator's entries. Every string was matched against the entity dictionary "
                   "before this record was written, and none matched.",
    }
    check_public_shape(record)
    _refuse_entities(record, entities)
    return record


# --------------------------------------------------------------------------- #
# The acceptance
# --------------------------------------------------------------------------- #


def _write_once(files: Mapping[Path, bytes]) -> None:
    for target, data in files.items():
        if target.exists() and target.read_bytes() != data:
            raise AcceptanceRefused(
                f"{target.parent.name} already holds an acceptance that differs from this one "
                f"({target.name}). A signed record is never overwritten; a new acceptance is a "
                f"successor, written into a new directory."
            )
    for target, data in files.items():
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(data.decode("utf-8"), target)


def accept(
    *,
    derivative: Path,
    derivative_sha256: str,
    policy: LoadedPolicy,
    policy_sha256: str,
    dictionary: Path,
    dictionary_sha256: str,
    stage_logs: Sequence[Path],
    table_row_map: Path,
    rewrite_plan: Path,
    structural_fidelity: Path,
    leak_scan: Path,
    reidentification_report: Path,
    reidentification_details: Path,
    operator_input: Path,
    out_dir: Path,
) -> AcceptanceResult:
    """Bind every stage record of *derivative*, and write the private and public records.

    *stage_logs* are the A2 and A4 logs, in the order the A6 report bound them.
    Every refusal runs before anything is written. A re-run that would write
    the same records is a no-op; one that would write different records is
    refused.
    """
    derivative = intake.require_private(derivative, "the derivative")
    dictionary_path = intake.require_private(dictionary, "the entity dictionary")
    out_dir = intake.require_private(out_dir, "the acceptance directory")
    intake.pin(derivative, derivative_sha256, "the derivative")
    size = derivative.stat().st_size
    require_hash(policy, policy_sha256)
    entities = matching.load_dictionary(dictionary_path, policy)
    if entities.sha256 != dictionary_sha256:
        raise AcceptanceRefused(
            f"the entity dictionary hashes to {entities.sha256}, not the declared "
            f"{dictionary_sha256}: this is not the pinned dictionary. Nothing was written."
        )

    scan = _read(leak_scan, "the leak scan report")
    report = _read(reidentification_report, "the re-identification report")
    details = _read(reidentification_details, "the re-identification details")
    fid = _read(structural_fidelity, "the structural fidelity report")
    plan = _read(rewrite_plan, "the rewrite plan")
    row_map = _read(table_row_map, "the Table 1.4.1 row map")
    logs = [_read(p, "a stage log") for p in stage_logs]
    operator = _operator(_read(operator_input, "the operator's input"), derivative_sha256)

    _require_schema(scan, scan_stage.SCHEMA, "the leak scan report")
    _require_schema(report, attack.SCHEMA, "the re-identification report")
    _require_schema(details, attack.DETAILS_SCHEMA, "the re-identification details")
    _require_schema(fid, fidelity.SCHEMA, "the structural fidelity report")
    _require_schema(row_map, table.ROW_MAP_SCHEMA, "the Table 1.4.1 row map")
    for bound, value in (
        (scan, _field(scan.record, "the leak scan report", "input", "sha256")),
        (report, _field(report.record, "the re-identification report", "input",
                        "derivative_sha256")),
        (details, details.record.get("derivative_sha256")),
        (fid, _field(fid.record, "the structural fidelity report", "input",
                     "derivative_sha256")),
    ):
        if value != derivative_sha256:
            raise AcceptanceRefused(
                f"{bound.name} is a record of another derivative ({value}), not of "
                f"{derivative_sha256}. Every record an acceptance binds describes the file "
                f"being accepted. Nothing was written."
            )
    for bound, what in ((scan, "the leak scan report"), (report, "the re-identification report"),
                        (fid, "the structural fidelity report")):
        _require_same(bound.record.get("policy_sha256"), policy.sha256, what, "the policy")
    for bound, what in ((scan, "the leak scan report"), (report, "the re-identification report")):
        _require_same(bound.record.get("dictionary_sha256"), entities.sha256, what,
                      "the dictionary")

    chain = _stage_chain(fid, logs)
    a2 = _redaction_log(logs)
    a4 = _table_log(logs)
    a2_output = _field(a2.record, "the A2 log", "output", "sha256")
    if _field(row_map.record, "the Table 1.4.1 row map", "output", "sha256") != (
        _field(a4.record, "the A4 log", "output", "sha256")
    ):
        raise AcceptanceRefused(
            "the Table 1.4.1 row map was written for another A4 output than the one in the "
            "stage chain. The mapping table binds the row map of this table."
        )
    rewritten = _rewrite(plan, a2_output, report, policy.sha256)

    a4_table = _field(a4.record, "the A4 log", "table")
    model = _field(report.record, "the re-identification report", "model")
    mapping = {
        "dictionary_sha256": entities.sha256,
        "edit_logs": [{"stage": link["stage"], "sha256": link["sha256"]} for link in chain],
        "table_row_map_sha256": row_map.sha256,
    }
    private = {
        "schema": SCHEMA,
        "record_type": RECORD_TYPE,
        "stage": "A7",
        "purpose": "The operator's full acceptance of an anonymised derivative: every stage "
                   "record bound by hash, the mapping table's parts and the re-identification "
                   "details. Private, D4.",
        "derivative": {"sha256": derivative_sha256, "bytes": size},
        "policy": {"policy_id": policy.record.get("policy_id"),
                   "policy_version": policy.version, "sha256": policy.sha256},
        "records": {
            "leak_scan": scan.binding(),
            "reidentification_report": report.binding(),
            "reidentification_details": details.binding(),
            "structural_fidelity": fid.binding(),
            "rewrite_plan": plan.binding(),
            "table_row_map": row_map.binding(),
            "stage_logs": chain,
        },
        "mapping_table": {**mapping, "sha256": hashlib.sha256(
            canonical_json_bytes(mapping)).hexdigest(),
            "sha256_basis": "sha256 of the canonical JSON of the three parts above"},
        "reidentification": {
            "leak_scan": {"verdict": scan.record.get("verdict"),
                          "counts": _field(scan.record, "the leak scan report", "counts")},
            "model_attack": _attack_summary(report.record),
            "details": {"reidentification_details_sha256": details.sha256,
                        "leak_scan_report_sha256": scan.sha256,
                        "leak_scan_review_items": len(scan.record.get("review") or [])},
        },
        "structural_fidelity": {"verdict": fid.record.get("verdict"),
                                "counts": _field(fid.record, "the structural fidelity report",
                                                 "counts")},
        "rewrite": rewritten,
        "table_1_4_1": {"synthetic": True, "data_rows": a4_table.get("data_rows"),
                        "columns": a4_table.get("columns")},
        "models": {
            "a3": {"model_id": rewritten["model_id"],
                   "canonical_model_id": canonical_model_id(rewritten["model_id"])},
            "a5": {"model_id": model.get("model_id"),
                   "canonical_model_id": canonical_model_id(model.get("model_id"))},
        },
        "operator": operator,
        "privacy": "Private: it names the private records by file and binds the mapping table "
                   "and the re-identification details. Its public counterpart holds metadata "
                   "only.",
    }
    private_bytes = canonical_json_bytes(private)
    public = public_record(private, private_sha256=hashlib.sha256(private_bytes).hexdigest(),
                           entities=entities)
    _write_once({out_dir / PRIVATE_FILE: private_bytes,
                 out_dir / PUBLIC_FILE: canonical_json_bytes(public)})
    return AcceptanceResult(out_dir / PRIVATE_FILE, out_dir / PUBLIC_FILE, public)
