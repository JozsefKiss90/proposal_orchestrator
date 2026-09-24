"""
Dev-graph revisions — contracts, candidate versions and assessment
applicability.

Three operations, each closed over declared data:

* :func:`check_revision` — a pure function over a :class:`RevisionContract`
  and a proposed change set (the diff :func:`runner.dev_graph.changes.change_set`
  produces). It returns one verdict from :data:`CONTRACT_VERDICTS`:
  ``rejected`` names every protected node the change touches; ``flagged_for_review``
  carries every change class the contract does not permit and every
  unresolved item the change bears on; ``accepted`` is the rest. Rejection
  outranks review. An unresolved item stays ``unresolved`` in the result
  whatever the verdict: nothing here approves anything.

* :func:`create_candidate_version` — after an accepted change the operator
  imports a new candidate as a second immutable document snapshot whose
  provenance names the snapshot it supersedes, the change record and the
  evidence nodes it rests on. The old record is left byte for byte as it
  was; the builder turns the provenance into the ``supersedes`` edge and
  :func:`runner.dev_graph.builder.current_commitments` stops returning the
  old snapshot's commitments.

* :func:`check_applicability` — a pure function over an assessment node and
  a current candidate version. An assessment binds the candidate id and
  version, a profile version and a policy version at the time it was made;
  a change to any of the three makes it not applicable, with one reason per
  changed binding from :data:`APPLICABILITY_REASONS`. The assessment node is
  read, never written.

Change classes. A change set is classified by a closed lookup, never by
inference: an added or removed edge takes the class of its predicate; an
added or removed node takes the class of its type; a directly changed node
takes the class of each changed field where the field is in the table and
the class of its type otherwise. A contained change (a work package whose
task changed) carries no class of its own.

The revision record writer is a registered deterministic component. It
reads the operator request, loads the change record, runs the check, creates
the candidate version only on ``accepted``, and writes one immutable record
under :data:`REVISIONS_REL`. No wall-clock field; the component's run id does
not enter the artifact; byte-equal replay.

Constitutional authority:
    Subordinate to CLAUDE.md. Writes only under Tier 4 dev_graph (documents,
    revisions). Evaluates no gate, invokes no Claude, invents no facts
    (§13.3), never approves a claim or a commitment (§12.2).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from runner.atomic_write import atomic_write_json
from runner.dev_graph.builder import Snapshot, build_snapshot
from runner.dev_graph.changes import read_change_record
from runner.dev_graph.documents import (
    DocumentRef,
    document_node_id,
    import_document,
    read_candidate,
)
from runner.dev_graph.identity import HASH_PREFIX, content_hash
from runner.dev_graph.policies import POLICY_VERSION
from runner.dev_graph.schema import NODE_TYPES, RELATIONSHIPS, DevGraphError

REVISION_SCHEMA_ID = "orch.dev_graph.revision_record.v1"

_DEV_GRAPH = "docs/tier4_orchestration_state/dev_graph"
#: One immutable revision record per revision id.
REVISIONS_REL = f"{_DEV_GRAPH}/revisions"
#: The operator request the writer reads.
REVISION_REQUEST_REL = f"{_DEV_GRAPH}/revision_request.json"

CONTRACT_VERDICTS: frozenset[str] = frozenset({"accepted", "rejected", "flagged_for_review"})
APPLICABILITY_REASONS: frozenset[str] = frozenset(
    {"candidate_version_changed", "profile_version_changed", "policy_version_changed"}
)
#: The one status an unresolved item can hold in a contract or a result.
_UNRESOLVED = "unresolved"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

# ---------------------------------------------------------------------------
# Change classes (closed lookups)
# ---------------------------------------------------------------------------

#: The class of an added or removed edge, by predicate. Every predicate in
#: the closed relationship set has one entry (pinned by test).
_PREDICATE_CLASS: Mapping[str, str] = {
    "assigned_to": "responsibility",
    "contributes_to": "contribution",
    "consumes": "dependency",
    "produces": "output",
    "validated_by": "validation",
    "constrained_by": "constraint",
    "supported_by": "evidence",
    "expressed_in": "wording",
    "addresses": "wording",
    "supersedes": "wording",
}

#: The class of an added, removed or changed node, by type. Every type in the
#: closed node-type set has one entry (pinned by test).
_TYPE_CLASS: Mapping[str, str] = {
    "participant": "participant",
    "objective": "objective",
    "work_package": "scope",
    "task": "scope",
    "deliverable": "output",
    "milestone": "validation",
    "source": "evidence",
    "source_span": "evidence",
    "claim": "wording",
    "commitment": "wording",
    "passage": "wording",
    "artifact_version": "wording",
    "execution": "execution_record",
    "assessment": "execution_record",
    "finding": "execution_record",
    "change_request": "execution_record",
    "revision_contract": "execution_record",
}

#: The class of a directly changed field, by ``(type, field)``. A field not
#: listed takes its type's class.
_FIELD_CLASS: Mapping[tuple[str, str], str] = {
    ("task", "responsible_partner"): "responsibility",
    ("task", "contributing_partners"): "contribution",
    ("task", "dependencies"): "dependency",
    ("task", "start_month"): "timing",
    ("task", "end_month"): "timing",
    ("work_package", "lead_partner"): "responsibility",
    ("work_package", "objectives"): "contribution",
    ("work_package", "constraints"): "constraint",
    ("work_package", "start_month"): "timing",
    ("work_package", "end_month"): "timing",
    ("deliverable", "produced_by"): "output",
    ("deliverable", "due_month"): "timing",
    ("milestone", "deliverables"): "validation",
    ("milestone", "due_month"): "timing",
}

#: The closed set of change classes a contract may permit.
CHANGE_CLASSES: frozenset[str] = frozenset(
    set(_PREDICATE_CLASS.values()) | set(_TYPE_CLASS.values()) | set(_FIELD_CLASS.values())
)

assert set(_PREDICATE_CLASS) == set(RELATIONSHIPS), "every predicate needs a change class"
assert set(_TYPE_CLASS) == NODE_TYPES, "every node type needs a change class"


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------


def _refuse(kind: str, offender: str, message: str) -> DevGraphError:
    return DevGraphError(kind, offender, message)


@dataclass(frozen=True)
class RevisionContract:
    """What one revision may change, what it may not touch, and what is open."""

    contract_id: str
    permitted_change_classes: frozenset[str]
    protected_node_ids: frozenset[str]
    unresolved_items: tuple[dict[str, Any], ...]
    """Each ``{item_id, description, node_ids, status: "unresolved"}``. An item
    with no ``node_ids`` bears on every change under the contract."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "permitted_change_classes": sorted(self.permitted_change_classes),
            "protected_node_ids": sorted(self.protected_node_ids),
            "unresolved_items": [dict(i) for i in self.unresolved_items],
        }


def _id_list(raw: Any, where: str, key: str) -> list[str]:
    value = raw.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise _refuse("malformed_request", where, f"{where}: {key} must be a list of ids")
    bad = next((v for v in value if not _ID_RE.match(v)), None)
    if bad is not None:
        raise _refuse("malformed_request", where, f"{where}: {key} entry {bad!r} is not a plain identifier")
    return list(value)


def _unresolved_item(raw: Any, where: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise _refuse("malformed_request", where, f"{where}: unresolved item is not an object")
    item_id = raw.get("item_id")
    if not isinstance(item_id, str) or not _ID_RE.match(item_id):
        raise _refuse("malformed_request", where, f"{where}: unresolved item needs a plain item_id")
    status = raw.get("status", _UNRESOLVED)
    if status != _UNRESOLVED:
        raise _refuse(
            "malformed_request",
            f"{where} item {item_id}",
            f"unresolved item {item_id} carries status {status!r}; the only status is {_UNRESOLVED!r}",
        )
    description = raw.get("description", "")
    if not isinstance(description, str):
        raise _refuse("malformed_request", f"{where} item {item_id}", "description must be a string")
    return {
        "item_id": item_id,
        "description": description,
        "node_ids": sorted(_id_list(raw, f"{where} item {item_id}", "node_ids")),
        "status": _UNRESOLVED,
    }


def normalise_contract(raw: Any) -> RevisionContract:
    """Validate a contract's declared shape, or refuse (``malformed_request``)."""
    if not isinstance(raw, dict):
        raise _refuse("malformed_request", "contract", "contract must be a JSON object")
    contract_id = raw.get("contract_id")
    if not isinstance(contract_id, str) or not _ID_RE.match(contract_id):
        raise _refuse("malformed_request", "contract", "contract_id must be a plain identifier")
    where = f"contract {contract_id}"
    classes = raw.get("permitted_change_classes", [])
    if not isinstance(classes, list) or not all(isinstance(c, str) for c in classes):
        raise _refuse("malformed_request", where, f"{where}: permitted_change_classes must be a list")
    unknown = next((c for c in classes if c not in CHANGE_CLASSES), None)
    if unknown is not None:
        raise _refuse(
            "malformed_request",
            where,
            f"{where}: change class {unknown!r} is not in {sorted(CHANGE_CLASSES)}",
        )
    items_raw = raw.get("unresolved_items", [])
    if items_raw is None:
        items_raw = []
    if not isinstance(items_raw, list):
        raise _refuse("malformed_request", where, f"{where}: unresolved_items must be a list")
    items = [_unresolved_item(i, where) for i in items_raw]
    ids = [i["item_id"] for i in items]
    dup = next((i for i in ids if ids.count(i) > 1), None)
    if dup is not None:
        raise _refuse("malformed_request", where, f"{where}: unresolved item {dup!r} declared more than once")
    return RevisionContract(
        contract_id=contract_id,
        permitted_change_classes=frozenset(classes),
        protected_node_ids=frozenset(_id_list(raw, where, "protected_node_ids")),
        unresolved_items=tuple(items),
    )


# ---------------------------------------------------------------------------
# The checker (pure)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContractCheck:
    """The outcome of checking one change set against one contract."""

    contract_id: str
    verdict: str
    change_classes: tuple[str, ...]
    protected_hits: tuple[dict[str, Any], ...]
    """Each ``{node_id, via}``: the changed nodes and edge labels that touch it."""
    unpermitted_classes: tuple[str, ...]
    unresolved: tuple[dict[str, Any], ...]
    """The contract's items, each with ``bears_on_change`` and ``via``; status
    stays ``unresolved``."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "verdict": self.verdict,
            "change_classes": list(self.change_classes),
            "protected_hits": [dict(h) for h in self.protected_hits],
            "unpermitted_classes": list(self.unpermitted_classes),
            "unresolved": [dict(i) for i in self.unresolved],
        }


def _touches(change_set: Mapping[str, Any]) -> dict[str, list[str]]:
    """Every node id the change set touches, with the reasons it is touched:
    ``changed:<id>`` for its own change, or the label of a changed edge it
    is an endpoint of. Sorted for determinism."""
    touched: dict[str, set[str]] = {}
    nodes, edges = change_set["nodes"], change_set["edges"]
    for n in nodes["added"] + nodes["removed"]:
        touched.setdefault(n["id"], set()).add(f"changed:{n['id']}")
    for c in nodes["changed"]:
        if c["kind"] == "direct":
            touched.setdefault(c["id"], set()).add(f"changed:{c['id']}")
    for e in edges["added"] + edges["removed"]:
        for end in (e["source"], e["target"]):
            touched.setdefault(end, set()).add(e["label"])
    return {nid: sorted(v) for nid, v in touched.items()}


def _validate_change_set(change_set: Any) -> None:
    try:
        nodes, edges = change_set["nodes"], change_set["edges"]
        for n in nodes["added"] + nodes["removed"]:
            if n["type"] not in _TYPE_CLASS:
                raise KeyError(n["type"])
        for c in nodes["changed"]:
            if c["type"] not in _TYPE_CLASS or c["kind"] not in ("direct", "contained"):
                raise KeyError(c["id"])
            list(c.get("changed_fields", []))
        for e in edges["added"] + edges["removed"]:
            if e["predicate"] not in _PREDICATE_CLASS:
                raise KeyError(e["predicate"])
            _ = e["source"], e["target"], e["label"]
    except (KeyError, TypeError) as exc:
        raise _refuse("malformed_request", "change_set", f"change set is not a snapshot diff: {exc!r}") from exc


def classify_change_set(change_set: Mapping[str, Any]) -> tuple[str, ...]:
    """The sorted change classes of a change set, by closed lookup."""
    _validate_change_set(change_set)
    classes: set[str] = set()
    nodes, edges = change_set["nodes"], change_set["edges"]
    for n in nodes["added"] + nodes["removed"]:
        classes.add(_TYPE_CLASS[n["type"]])
    for c in nodes["changed"]:
        if c["kind"] != "direct":
            continue
        fields = list(c.get("changed_fields", []))
        if not fields:
            classes.add(_TYPE_CLASS[c["type"]])
        for f in fields:
            classes.add(_FIELD_CLASS.get((c["type"], f), _TYPE_CLASS[c["type"]]))
    for e in edges["added"] + edges["removed"]:
        classes.add(_PREDICATE_CLASS[e["predicate"]])
    return tuple(sorted(classes))


def check_revision(contract: RevisionContract, change_set: Mapping[str, Any]) -> ContractCheck:
    """Check *change_set* against *contract*. Pure: reads both, writes neither.

    ``rejected`` when the change touches a protected node (each named with
    the reasons it is touched); else ``flagged_for_review`` when a change
    class is not permitted or an unresolved item bears on the change; else
    ``accepted``. Unresolved items are carried through unchanged in status.
    """
    if not isinstance(contract, RevisionContract):
        raise _refuse("malformed_request", "contract", "contract must be a RevisionContract (normalise_contract)")
    classes = classify_change_set(change_set)
    touched = _touches(change_set)

    hits = tuple(
        {"node_id": nid, "via": touched[nid]}
        for nid in sorted(contract.protected_node_ids)
        if nid in touched
    )
    unpermitted = tuple(c for c in classes if c not in contract.permitted_change_classes)
    unresolved: list[dict[str, Any]] = []
    for item in contract.unresolved_items:
        if item["node_ids"]:
            via = sorted(v for nid in item["node_ids"] if nid in touched for v in touched[nid])
            bears = bool(via)
        else:
            via, bears = [], bool(touched)
        unresolved.append({**item, "status": _UNRESOLVED, "bears_on_change": bears, "via": via})

    if hits:
        verdict = "rejected"
    elif unpermitted or any(i["bears_on_change"] for i in unresolved):
        verdict = "flagged_for_review"
    else:
        verdict = "accepted"
    return ContractCheck(
        contract_id=contract.contract_id,
        verdict=verdict,
        change_classes=classes,
        protected_hits=hits,
        unpermitted_classes=unpermitted,
        unresolved=tuple(unresolved),
    )


# ---------------------------------------------------------------------------
# Candidate versioning
# ---------------------------------------------------------------------------


def _node_index(snapshot: Snapshot) -> dict[str, dict[str, Any]]:
    return {n["id"]: n for n in snapshot.nodes}


def build_provenance(
    snapshot: Snapshot,
    *,
    supersedes: str,
    change_id: str,
    evidence: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """The provenance a new candidate version carries, resolved against
    *snapshot*: the superseded snapshot as ``{id, version}``, the change id,
    and each evidence node as ``{id, version}``. Pure over the snapshot."""
    nodes = _node_index(snapshot)
    prev = nodes.get(supersedes)
    if prev is None or prev["type"] != "artifact_version":
        raise _refuse("malformed_request", str(supersedes), f"no document snapshot {supersedes!r} in the current build")
    refs: list[dict[str, str]] = []
    for eid in sorted(set(evidence)):
        node = nodes.get(eid)
        if node is None:
            raise _refuse("malformed_request", str(eid), f"evidence node {eid!r} is not in the current build")
        refs.append({"id": eid, "version": node["version"]})
    return {
        "supersedes": {"id": supersedes, "version": prev["version"]},
        "change_id": change_id,
        "evidence": refs,
    }


def create_candidate_version(
    repo_root: Path,
    candidate_rel: Path | str,
    *,
    supersedes: str,
    change_id: str,
    evidence: list[str] | tuple[str, ...] = (),
    state: str = "draft",
) -> DocumentRef:
    """Import the candidate at *candidate_rel* as the version that supersedes
    the document snapshot *supersedes*, with provenance to *change_id* and the
    *evidence* nodes.

    Refuses (``malformed_request``) before writing when the predecessor or an
    evidence node is not in the current build, the change record does not
    exist, or the candidate would supersede itself. Re-running with the same
    inputs is a no-op; the same content under other provenance is refused
    (``immutable_record``). The predecessor record is never touched.
    """
    root = Path(repo_root)
    change = read_change_record(root, change_id)
    snapshot = build_snapshot(root)
    provenance = build_provenance(snapshot, supersedes=supersedes, change_id=change.change_id, evidence=evidence)
    content = read_candidate(root, candidate_rel)
    new_id = document_node_id(content["document_id"], content_hash(content))
    if new_id == supersedes:
        raise _refuse(
            "malformed_request",
            new_id,
            f"candidate content is the snapshot {supersedes} it would supersede; a version needs a change",
        )
    return import_document(root, candidate_rel, state=state, provenance=provenance)


# ---------------------------------------------------------------------------
# Assessment applicability (pure)
# ---------------------------------------------------------------------------


def _ref(node: Mapping[str, Any]) -> dict[str, str]:
    return {"id": str(node["id"]), "version": str(node["version"])}


def bind_assessment(
    assessment_id: str,
    candidate: Mapping[str, Any],
    *,
    profile_version: str,
    policy_version: str = POLICY_VERSION,
    content: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """An ``assessment`` node bound to *candidate* (``{id, version}`` or a
    document node), a profile version and a policy version. The binding is
    part of the node content, so the node version pins it. Pure."""
    if not isinstance(assessment_id, str) or not _ID_RE.match(assessment_id):
        raise _refuse("malformed_request", str(assessment_id), "assessment id must be a plain identifier")
    body = {
        **(dict(content) if content else {}),
        "binding": {
            "candidate": _ref(candidate),
            "profile_version": str(profile_version),
            "policy_version": str(policy_version),
        },
    }
    return {
        "id": assessment_id,
        "type": "assessment",
        "version": content_hash(body),
        "title": assessment_id,
        "path": "",
        "content": body,
    }


@dataclass(frozen=True)
class Applicability:
    """Whether an assessment still applies to a current candidate version."""

    assessment: dict[str, str]
    applicable: bool
    reasons: tuple[str, ...]
    bound: dict[str, Any]
    current: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment": dict(self.assessment),
            "applicable": self.applicable,
            "reasons": list(self.reasons),
            "bound": dict(self.bound),
            "current": dict(self.current),
        }


def _binding_of(assessment: Mapping[str, Any]) -> dict[str, Any]:
    where = str(assessment.get("id", "assessment"))
    if assessment.get("type") != "assessment":
        raise _refuse("malformed_record", where, f"node {where} is {assessment.get('type')!r}, not an assessment")
    binding = (assessment.get("content") or {}).get("binding")
    if not isinstance(binding, dict):
        raise _refuse("malformed_record", where, f"assessment {where} carries no binding")
    try:
        return {
            "candidate": _ref(binding["candidate"]),
            "profile_version": str(binding["profile_version"]),
            "policy_version": str(binding["policy_version"]),
        }
    except (KeyError, TypeError) as exc:
        raise _refuse("malformed_record", where, f"assessment {where} binding is incomplete: {exc!r}") from exc


def check_applicability(
    assessment: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    profile_version: str,
    policy_version: str = POLICY_VERSION,
) -> Applicability:
    """Whether *assessment* applies to the current *candidate* version under
    the current profile and policy versions. Pure: the assessment is read,
    never mutated, and the result is a separate value."""
    bound = _binding_of(assessment)
    current = {
        "candidate": _ref(candidate),
        "profile_version": str(profile_version),
        "policy_version": str(policy_version),
    }
    reasons: list[str] = []
    if bound["candidate"] != current["candidate"]:
        reasons.append("candidate_version_changed")
    if bound["profile_version"] != current["profile_version"]:
        reasons.append("profile_version_changed")
    if bound["policy_version"] != current["policy_version"]:
        reasons.append("policy_version_changed")
    return Applicability(
        assessment=_ref(assessment),
        applicable=not reasons,
        reasons=tuple(reasons),
        bound=bound,
        current=current,
    )


# ---------------------------------------------------------------------------
# The revision record writer (registered deterministic component)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RevisionRecord:
    """The durable outcome of one revision request."""

    revision_id: str
    change_id: str
    contract: RevisionContract
    check: ContractCheck
    candidate_version: dict[str, Any] | None
    """``{previous: {id, version}, created: {id, version, path, provenance}}``
    on an accepted check that created a version; ``None`` otherwise."""
    path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": REVISION_SCHEMA_ID,
            "revision_id": self.revision_id,
            "change_id": self.change_id,
            "contract": self.contract.to_dict(),
            "check": self.check.to_dict(),
            "candidate_version": dict(self.candidate_version) if self.candidate_version else None,
        }


def read_revision_request(repo_root: Path) -> dict[str, Any]:
    """The operator request, validated for shape, or refuse (``malformed_request``)."""
    path = Path(repo_root) / REVISION_REQUEST_REL
    if not path.is_file():
        raise _refuse("malformed_request", REVISION_REQUEST_REL, "no revision request")
    try:
        req = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise _refuse("malformed_request", REVISION_REQUEST_REL, f"unreadable JSON: {exc}") from exc
    if not isinstance(req, dict):
        raise _refuse("malformed_request", REVISION_REQUEST_REL, "request must be a JSON object")
    for key in ("revision_id", "change_id", "supersedes", "candidate"):
        if not isinstance(req.get(key), str) or not req[key]:
            raise _refuse("malformed_request", REVISION_REQUEST_REL, f"request needs a non-empty string {key!r}")
    if not _ID_RE.match(req["revision_id"]):
        raise _refuse("malformed_request", req["revision_id"], "revision_id is not a plain identifier")
    evidence = req.get("evidence", [])
    if not isinstance(evidence, list) or not all(isinstance(e, str) for e in evidence):
        raise _refuse("malformed_request", REVISION_REQUEST_REL, "evidence must be a list of node ids")
    return {
        "revision_id": req["revision_id"],
        "change_id": req["change_id"],
        "contract": normalise_contract(req.get("contract")),
        "candidate": req["candidate"],
        "supersedes": req["supersedes"],
        "evidence": list(evidence),
    }


def write_revision_record(repo_root: Path) -> list[Path]:
    """Run the request under :data:`REVISION_REQUEST_REL`; write the record.

    Loads the change record, checks it against the contract, creates the
    candidate version only on ``accepted``, and writes
    ``<revisions>/<revision_id>.json``. A revision id is write-once: a
    second run with the same inputs finds the same bytes and is a no-op; a
    run that would write different bytes under an existing id is refused
    (``immutable_record``). Refuses before writing anything on a missing
    change record or a malformed request or contract.
    """
    root = Path(repo_root)
    req = read_revision_request(root)
    target_rel = Path(REVISIONS_REL) / f"{req['revision_id']}.json"
    target = root / target_rel
    change = read_change_record(root, req["change_id"])
    check = check_revision(req["contract"], change.change_set)

    existing: dict[str, Any] | None = None
    if target.is_file():
        # Write-once, checked before any document write: an existing record
        # must already describe this change, contract and verdict.
        existing = json.loads(target.read_text(encoding="utf-8-sig"))
        head = {k: existing.get(k) for k in ("change_id", "contract", "check")}
        if head != {"change_id": change.change_id, "contract": req["contract"].to_dict(), "check": check.to_dict()}:
            raise _refuse(
                "immutable_record", target_rel.as_posix(), f"revision {req['revision_id']} is already recorded with other content"
            )

    version: dict[str, Any] | None = None
    if check.verdict == "accepted":
        # Re-running with the same inputs finds the same document record and
        # is a no-op; other evidence or another candidate under an existing
        # record is refused by the record's own immutability.
        ref = create_candidate_version(
            root,
            req["candidate"],
            supersedes=req["supersedes"],
            change_id=change.change_id,
            evidence=req["evidence"],
        )
        provenance = json.loads((root / ref.path).read_text(encoding="utf-8-sig"))["provenance"]
        version = {
            "previous": dict(provenance["supersedes"]),
            "created": {"id": ref.id, "version": ref.version, "path": ref.path, "provenance": provenance},
        }

    record = RevisionRecord(
        revision_id=req["revision_id"],
        change_id=change.change_id,
        contract=req["contract"],
        check=check,
        candidate_version=version,
        path=target_rel.as_posix(),
    )
    doc = record.to_dict()
    if existing is not None:
        if existing != doc:
            raise _refuse("immutable_record", target_rel.as_posix(), f"revision {req['revision_id']} is already recorded with other content")
        return [target]
    atomic_write_json(doc, target)
    return [target]


def read_revision_record(repo_root: Path, revision_id: str) -> RevisionRecord:
    """The recorded revision *revision_id*, or refuse (``malformed_request``)."""
    root = Path(repo_root)
    if not isinstance(revision_id, str) or not _ID_RE.match(revision_id):
        raise _refuse("malformed_request", str(revision_id), "revision_id is not a plain identifier")
    rel = Path(REVISIONS_REL) / f"{revision_id}.json"
    path = root / rel
    if not path.is_file():
        raise _refuse("malformed_request", rel.as_posix(), f"no revision record {revision_id}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise _refuse("malformed_record", rel.as_posix(), f"unreadable JSON: {exc}") from exc
    try:
        if doc["schema_id"] != REVISION_SCHEMA_ID:
            raise KeyError("schema_id")
        check = doc["check"]
        if check["verdict"] not in CONTRACT_VERDICTS:
            raise KeyError("verdict")
        return RevisionRecord(
            revision_id=doc["revision_id"],
            change_id=doc["change_id"],
            contract=normalise_contract(doc["contract"]),
            check=ContractCheck(
                contract_id=check["contract_id"],
                verdict=check["verdict"],
                change_classes=tuple(check["change_classes"]),
                protected_hits=tuple(check["protected_hits"]),
                unpermitted_classes=tuple(check["unpermitted_classes"]),
                unresolved=tuple(check["unresolved"]),
            ),
            candidate_version=doc.get("candidate_version"),
            path=rel.as_posix(),
        )
    except (KeyError, TypeError) as exc:
        raise _refuse("malformed_record", rel.as_posix(), f"not a {REVISION_SCHEMA_ID} record: {exc!r}") from exc


def run_revision_record_writer(run_id: str, repo_root: Path) -> list[Path]:
    """Component adapter: ``(run_id, repo_root) -> written``. The run id is
    accepted for the contract and does not enter the artifact."""
    del run_id
    return write_revision_record(repo_root)
