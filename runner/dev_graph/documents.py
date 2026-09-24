"""
Dev-graph document snapshots — importing a candidate as an immutable record.

An operator imports a candidate proposal document (a JSON file with sections,
claims and commitments). The import validates the candidate's own shape,
computes a content-derived version, and writes one immutable record under
:data:`DOCUMENTS_REL`. The record is the snapshot builder's only source for
document, passage, claim and commitment nodes.

Immutability model:

* The record path is ``<document_id>/<version hex>.json``. Importing the same
  content again lands on the same path with the same bytes: a no-op.
* Changed content is a new version at a new path. The old record stays.
* Same content under a different lifecycle state is refused. A state
  transition is not a re-import; the revision ticket adds ``supersedes``.
* No wall-clock field. The record carries nothing a replay could change.

Candidate shape (all keys are the candidate's own declarations):

    {
      "document_id": "...", "title": "...",
      "sections":    [{"section_id", "title", "content", "addresses": [ids]}],
      "claims":      [{"claim_id", "section_id", "text", "evidence_strength",
                       "verified_span": {"source_id", "start", "end", "version"?} | absent,
                       "approval", "declared_status"?}],
      "commitments": [{"commitment_id", "section_id", "text", "addresses": [ids]}]
    }

The three claim evidence fields stay separate. ``declared_status`` is fed by
the evidence-strength lookup only (``runner.graph_schema.EVIDENCE_TO_STATUS``);
the one permitted declaration is ``Assumed`` over an ``Unresolved`` lookup,
mirroring the assumption applier's flip. ``verified_span`` and ``approval``
are stored as declared and never derived from the status.

Constitutional authority:
    Subordinate to CLAUDE.md. Writes only under Tier 4 dev_graph/documents,
    evaluates no gate, invokes no Claude, invents no facts (§13.3).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from runner.atomic_write import atomic_write_json
from runner.dev_graph.identity import HASH_PREFIX, content_hash
from runner.dev_graph.schema import (
    APPROVALS,
    DECLARED_STATUSES,
    DOCUMENT_STATES,
    DevGraphError,
)
from runner.graph_schema import EVIDENCE_TO_STATUS

DOCUMENT_SCHEMA_ID = "orch.dev_graph.document_snapshot.v1"

#: Repo-relative directory holding one immutable record per document version.
DOCUMENTS_REL = "docs/tier4_orchestration_state/dev_graph/documents"

#: Node kind stamped on the ``artifact_version`` node a record becomes.
DOCUMENT_KIND = "document_snapshot"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_SHORT_HEX = 16


@dataclass(frozen=True)
class DocumentRef:
    """The identity of one imported document snapshot."""

    id: str
    """Node id: ``<document_id>@<version hex prefix>``."""
    version: str
    """Content hash of the node content the builder will index."""
    path: str
    """Repo-relative POSIX path of the immutable record."""


# ---------------------------------------------------------------------------
# Candidate validation (pure)
# ---------------------------------------------------------------------------


def _malformed(where: str, message: str) -> DevGraphError:
    return DevGraphError("malformed_record", where, message)


def _str(rec: dict[str, Any], key: str, where: str, *, required: bool = True) -> str:
    value = rec.get(key)
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise _malformed(where, f"{where}: {key!r} must be a non-empty string")
    return value


def _ids(rec: dict[str, Any], key: str, where: str) -> list[str]:
    value = rec.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise _malformed(where, f"{where}: {key!r} must be a list of ids")
    return list(value)


def _objects(rec: dict[str, Any], key: str, where: str) -> Iterator[dict[str, Any]]:
    value = rec.get(key, [])
    if value is None:
        return
    if not isinstance(value, list):
        raise _malformed(where, f"{where}: {key!r} must be a list")
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise _malformed(where, f"{where}: {key}[{i}] is not an object")
        yield item


def _section(s: dict[str, Any], where: str) -> dict[str, Any]:
    sid = _str(s, "section_id", where)
    if not _ID_RE.match(sid):
        raise _malformed(where, f"{where}: section_id {sid!r} is not a plain identifier")
    return {
        "section_id": sid,
        "title": _str(s, "title", f"section {sid}", required=False),
        "content": _str(s, "content", f"section {sid}", required=False),
        "addresses": _ids(s, "addresses", f"section {sid}"),
    }


def _verified_span(raw: Any, where: str) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise _malformed(where, f"{where}: verified_span must be an object or absent")
    source_id = _str(raw, "source_id", where)
    start, end = raw.get("start"), raw.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or isinstance(start, bool) or isinstance(end, bool):
        raise _malformed(where, f"{where}: verified_span offsets must be integers")
    if start < 0 or end <= start:
        raise _malformed(where, f"{where}: verified_span offset range {start}-{end} is empty or negative")
    span: dict[str, Any] = {"source_id": source_id, "start": start, "end": end}
    version = raw.get("version")
    if version is not None:
        if not isinstance(version, str) or not version.startswith(HASH_PREFIX):
            raise _malformed(where, f"{where}: verified_span version must be a {HASH_PREFIX} hash")
        span["version"] = version
    return span


def _claim(c: dict[str, Any], sections: set[str], where_doc: str) -> dict[str, Any]:
    cid = _str(c, "claim_id", where_doc)
    where = f"claim {cid}"
    if not _ID_RE.match(cid):
        raise _malformed(where, f"{where}: claim_id is not a plain identifier")
    section_id = _str(c, "section_id", where)
    if section_id not in sections:
        raise _malformed(where, f"{where}: section_id {section_id!r} is not a section of the document")
    strength = _str(c, "evidence_strength", where)
    if strength not in EVIDENCE_TO_STATUS:
        raise _malformed(
            where,
            f"{where}: evidence_strength {strength!r} is not in the lookup "
            f"{sorted(EVIDENCE_TO_STATUS)}",
        )
    # The lookup is the only feed of the declared status ...
    declared = EVIDENCE_TO_STATUS[strength]
    # ... except the one flip the assumption applier also makes.
    override = c.get("declared_status")
    if override is not None:
        if override not in DECLARED_STATUSES:
            raise _malformed(where, f"{where}: declared_status {override!r} is not in {sorted(DECLARED_STATUSES)}")
        if override != declared and not (override == "Assumed" and declared == "Unresolved"):
            raise _malformed(
                where,
                f"{where}: declared_status {override!r} contradicts the lookup "
                f"({strength!r} -> {declared!r}); only Assumed over Unresolved may be declared",
            )
        declared = override
    approval = _str(c, "approval", where)
    if approval not in APPROVALS:
        raise _malformed(where, f"{where}: approval {approval!r} is not in {sorted(APPROVALS)}")
    return {
        "claim_id": cid,
        "section_id": section_id,
        "text": _str(c, "text", where, required=False),
        "evidence_strength": strength,
        "declared_status": declared,
        "verified_span": _verified_span(c.get("verified_span"), where),
        "approval": approval,
    }


def _commitment(m: dict[str, Any], sections: set[str], where_doc: str) -> dict[str, Any]:
    mid = _str(m, "commitment_id", where_doc)
    where = f"commitment {mid}"
    if not _ID_RE.match(mid):
        raise _malformed(where, f"{where}: commitment_id is not a plain identifier")
    section_id = _str(m, "section_id", where)
    if section_id not in sections:
        raise _malformed(where, f"{where}: section_id {section_id!r} is not a section of the document")
    return {
        "commitment_id": mid,
        "section_id": section_id,
        "text": _str(m, "text", where, required=False),
        "addresses": _ids(m, "addresses", where),
    }


def normalise_candidate(raw: Any, where: str) -> dict[str, Any]:
    """Validate a candidate's own shape and return its canonical content.

    Pure. Cross-record facts (does the source exist, do offsets fit its text,
    do the addressed ids exist) are the builder's job at snapshot time.
    """
    if not isinstance(raw, dict):
        raise _malformed(where, f"{where}: candidate must be a JSON object")
    document_id = _str(raw, "document_id", where)
    if not _ID_RE.match(document_id):
        raise _malformed(where, f"{where}: document_id {document_id!r} is not a plain identifier")
    sections = [_section(s, f"{where} section") for s in _objects(raw, "sections", where)]
    if not sections:
        raise _malformed(where, f"{where}: a candidate needs at least one section")
    ids = [s["section_id"] for s in sections]
    dup = next((i for i in ids if ids.count(i) > 1), None)
    if dup is not None:
        raise _malformed(where, f"{where}: section_id {dup!r} declared more than once")
    section_ids = set(ids)
    claims = [_claim(c, section_ids, where) for c in _objects(raw, "claims", where)]
    for key, items in (("claim_id", claims),):
        seen = [i[key] for i in items]
        dup = next((i for i in seen if seen.count(i) > 1), None)
        if dup is not None:
            raise _malformed(where, f"{where}: {key} {dup!r} declared more than once")
    commitments = [_commitment(m, section_ids, where) for m in _objects(raw, "commitments", where)]
    seen = [m["commitment_id"] for m in commitments]
    dup = next((i for i in seen if seen.count(i) > 1), None)
    if dup is not None:
        raise _malformed(where, f"{where}: commitment_id {dup!r} declared more than once")
    return {
        "document_id": document_id,
        "title": _str(raw, "title", where, required=False) or document_id,
        "sections": sections,
        "claims": claims,
        "commitments": commitments,
    }


# ---------------------------------------------------------------------------
# Rendering (pure)
# ---------------------------------------------------------------------------


def render_document(sections: list[dict[str, Any]]) -> tuple[str, dict[str, dict[str, int]]]:
    """Render the sections to one text and return it with each section's span.

    The layout is fixed (``## <id> <title>``, blank line, content, blank line)
    so a span is a stable function of the sections alone.
    """
    parts: list[str] = []
    spans: dict[str, dict[str, int]] = {}
    pos = 0
    for s in sections:
        block = f"## {s['section_id']} {s['title']}\n\n{s['content']}\n\n"
        spans[s["section_id"]] = {"start": pos, "end": pos + len(block)}
        parts.append(block)
        pos += len(block)
    return "".join(parts), spans


def node_content(record: dict[str, Any]) -> dict[str, Any]:
    """The content the builder indexes for the ``artifact_version`` node.

    Derived from the record alone: the rendered text is included so a span
    can be resolved from the snapshot without the record. Provenance, when
    the record carries it, is part of the node content, so a re-versioned
    candidate is a different node version from a plain import of the same
    text.
    """
    text, _ = render_document(record["sections"])
    content = {
        "kind": DOCUMENT_KIND,
        "document_id": record["document_id"],
        "title": record["title"],
        "state": record["state"],
        "content_version": record["content_version"],
        "sections": record["sections"],
        "text": text,
    }
    if record.get("provenance") is not None:
        content["provenance"] = record["provenance"]
    return content


def document_node_id(document_id: str, content_version: str) -> str:
    return f"{document_id}@{content_version[len(HASH_PREFIX):][:_SHORT_HEX]}"


# ---------------------------------------------------------------------------
# Import (the one write)
# ---------------------------------------------------------------------------


def read_candidate(repo_root: Path, candidate_rel: Path | str) -> dict[str, Any]:
    """The canonical content of the candidate file at *candidate_rel*, or refuse."""
    rel = Path(candidate_rel)
    where = rel.as_posix()
    path = Path(repo_root) / rel
    if not path.is_file():
        raise _malformed(where, "candidate file not found")
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise _malformed(where, f"unreadable JSON: {exc}") from exc
    return normalise_candidate(raw, where)


def import_document(
    repo_root: Path,
    candidate_rel: Path | str,
    *,
    state: str = "imported",
    provenance: dict[str, Any] | None = None,
) -> DocumentRef:
    """Import the candidate at *candidate_rel* as an immutable document record.

    Returns the :class:`DocumentRef` of the record, writing it only when it
    does not already exist. Raises :class:`DevGraphError` on an unreadable or
    malformed candidate or an unknown *state* (``malformed_record``), and on
    an existing record of the same content under another state or another
    provenance (``immutable_record``): neither is a re-import.

    *provenance* is stored as given and never derived here. The revision
    module (``runner.dev_graph.revisions.create_candidate_version``)
    validates it against the change record and the current snapshot before
    calling this function; the builder turns its ``supersedes`` reference
    into the edge.
    """
    root = Path(repo_root)
    rel = Path(candidate_rel)
    where = rel.as_posix()
    if state not in DOCUMENT_STATES:
        raise _malformed(where, f"state {state!r} is not in {sorted(DOCUMENT_STATES)}")
    content = read_candidate(root, rel)
    content_version = content_hash(content)
    record: dict[str, Any] = {
        "schema_id": DOCUMENT_SCHEMA_ID,
        "document_id": content["document_id"],
        "content_version": content_version,
        "state": state,
        **{k: content[k] for k in ("title", "sections", "claims", "commitments")},
    }
    if provenance is not None:
        record["provenance"] = provenance
    node_id = document_node_id(record["document_id"], content_version)
    target_rel = Path(DOCUMENTS_REL) / record["document_id"] / f"{content_version[len(HASH_PREFIX):]}.json"
    target = root / target_rel
    if target.is_file():
        existing = json.loads(target.read_text(encoding="utf-8-sig"))
        if existing != record:
            raise DevGraphError(
                "immutable_record",
                target_rel.as_posix(),
                f"document snapshot {node_id} already exists with state "
                f"{existing.get('state')!r}; a state or provenance change is not a re-import",
            )
    else:
        atomic_write_json(record, target)
    return DocumentRef(
        id=node_id, version=content_hash(node_content(record)), path=target_rel.as_posix()
    )


def read_document_records(repo_root: Path) -> list[tuple[str, dict[str, Any]]]:
    """Every record under :data:`DOCUMENTS_REL` as ``(rel_path, record)``, sorted by path."""
    base = Path(repo_root) / DOCUMENTS_REL
    if not base.is_dir():
        return []
    out: list[tuple[str, dict[str, Any]]] = []
    for p in sorted(base.rglob("*.json")):
        rel = p.relative_to(repo_root).as_posix()
        try:
            rec = json.loads(p.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise _malformed(rel, f"unreadable JSON: {exc}") from exc
        if not isinstance(rec, dict) or rec.get("schema_id") != DOCUMENT_SCHEMA_ID:
            raise _malformed(rel, f"not a {DOCUMENT_SCHEMA_ID} record")
        if rec.get("state") not in DOCUMENT_STATES:
            raise _malformed(rel, f"state {rec.get('state')!r} is not in {sorted(DOCUMENT_STATES)}")
        out.append((rel, rec))
    return out
