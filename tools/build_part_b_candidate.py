"""Build a blind-lane candidate document from Phase 8's Tier 5 section artifacts.

Phase 8 writes three section artifacts under
``docs/tier5_deliverables/proposal_sections/``. The blind pre-evaluation lane
imports a *candidate*: one JSON object carrying ``document_id``, ``sections``,
``claims`` and ``commitments``, which
``runner.dev_graph.documents.import_document`` turns into an immutable document
record. Nothing joined the two. ``import_document`` is called from the
revisions module and from tests, and every test hand-writes its candidate, so
the demo ticket "Candidate Part B and the blind baseline" had no route from a
drafted Part B to a graded one.

This tool is that route. It is deterministic and Claude-free: every field it
writes is copied from a section artifact, and it derives no prose and makes no
inference. It is **not** a skill (§17.5.2 defines a skill by Claude invocation)
and not a manifest-bound deterministic component (§17.5.3) — it is an operator
step run once after Phase 8, in the shape of ``tools/derive_run_phase_costs.py``.

**The anchor chain is why the copying must be exact.** The Tier 2A
``section_schema_registry`` declares the RIA sub-sections ``B.1.1`` to
``B.3.2``; the Phase 8 drafting skills take ``sub_section_id`` from that
registry; the RIA rubrics anchor on six of those seven. The evidence pack's
anchor map fails closed on an absent anchor, by design, so a converter that
renamed or renumbered a sub-section would break grading silently. Every
``sub_section_id`` here is carried verbatim.

**What it refuses.** A missing section artifact, a wrong ``schema_id``, a
``criterion`` that disagrees with the schema, an ``artifact_status`` of
``invalid``, a section with no sub-sections, a sub-section with no title or
content, a duplicate id, and an unknown claim status. It then checks the
finished candidate against ``normalise_candidate`` — the validator the importer
itself runs — so identifier shape is judged once, by its owner, rather than by
a second copy of the rule here.

Nothing is repaired. §12.4 makes a missing mandatory input a failure rather
than a partial output, and rewriting an id would break the traceability the id
exists for.

Run from the repository root::

    py -3.10 tools/build_part_b_candidate.py                 # write the candidate
    py -3.10 tools/build_part_b_candidate.py --check         # write nothing
    py -3.10 tools/build_part_b_candidate.py --document-id X

Importing it is a separate, deliberate act. The tool writes the candidate and
stops, so the operator decides when a durable document record is created.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from runner.atomic_write import atomic_write_json, canonical_json_bytes  # noqa: E402
from runner.dev_graph.documents import normalise_candidate  # noqa: E402
from runner.dev_graph.schema import DevGraphError  # noqa: E402
from runner.phase8_preseed import PRESEED_NODE_CONFIG  # noqa: E402

#: Where a candidate lives before import. Established by the dev-graph
#: fixtures and the eleven test modules that import from it; the ESR intake
#: decision record of 2026-09-24 names a fixture under the same directory.
CANDIDATES_REL = "docs/tier5_deliverables/candidates"

#: Phase 8's section artifacts.
SECTIONS_REL = "docs/tier5_deliverables/proposal_sections"

#: Every claim carries this approval. Nothing approved the demo's Part B, and
#: ``pending`` says so; ``approved`` would assert a review that never happened.
CLAIM_APPROVAL = "pending"

#: Tier 5 ``validation_status.claim_statuses[].status`` -> the graph's
#: ``evidence_strength``. The graph then derives ``declared_status`` from its
#: own lookup, so this map is the only translation and it is one way.
#: ``inferred`` maps to ``inference`` rather than ``synthesis``: both resolve to
#: Inferred, and a drafted claim marked inferred was reasoned to, not composed.
EVIDENCE_STRENGTH_BY_STATUS: dict[str, str] = {
    "confirmed": "source_grounded",
    "inferred": "inference",
    "unresolved": "unconfirmed",
}


class BuilderError(RuntimeError):
    """A section artifact is absent, malformed, or not safe to carry."""


@dataclass(frozen=True)
class SectionSpec:
    """One Phase 8 section: its canonical identity and its schema's demands.

    ``section_id`` is the artifact's filename stem, which is also the id the
    RIA profile's ``criteria[].section_ids`` names. The two agreeing is what
    lets a built candidate satisfy ``required_sections``.
    """

    section_id: str
    schema_id: str
    criterion: str


#: The criterion string each Tier 5 section schema fixes, in its own field
#: description ("Must equal ...").  Not owned by another module, unlike the
#: schema ids below, so it is declared here and checked against the artifact.
_CRITERION_BY_SECTION: dict[str, str] = {
    "excellence_section": "Excellence",
    "impact_section": "Impact",
    "implementation_section": "Quality and efficiency of the implementation",
}


def _section_specs() -> tuple[SectionSpec, ...]:
    """The three Phase 8 sections, with schema ids taken from their owner.

    ``runner.phase8_preseed.PRESEED_NODE_CONFIG`` already binds each Phase 8
    node to its target path and ``schema_id``, and that module asserts at
    import time that its own copies do not drift from their source. Restating
    the ids here would be a third copy free to drift from both, so they are
    read from it and keyed by the target filename stem.
    """
    by_stem = {
        Path(cfg["target_path"]).stem: cfg["schema_id"]
        for cfg in PRESEED_NODE_CONFIG.values()
    }
    specs = []
    for section_id, criterion in _CRITERION_BY_SECTION.items():
        schema_id = by_stem.get(section_id)
        if schema_id is None:
            raise BuilderError(
                f"{section_id}: PRESEED_NODE_CONFIG binds no Phase 8 node to "
                f"{section_id}.json, so its schema id cannot be resolved"
            )
        specs.append(
            SectionSpec(
                section_id=section_id, schema_id=schema_id, criterion=criterion
            )
        )
    return tuple(specs)


SECTION_SPECS: tuple[SectionSpec, ...] = _section_specs()


def _read_section(repo_root: Path, spec: SectionSpec) -> dict[str, Any]:
    """One section artifact, or refuse."""
    path = Path(repo_root) / SECTIONS_REL / f"{spec.section_id}.json"
    if not path.is_file():
        raise BuilderError(
            f"{spec.section_id}: no artifact at {path.as_posix()}. "
            "Phase 8 has not written this section, and two sections out of "
            "three is not a Part B."
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise BuilderError(f"{spec.section_id}: unreadable JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise BuilderError(f"{spec.section_id}: artifact must be a JSON object")

    declared = raw.get("schema_id")
    if declared != spec.schema_id:
        raise BuilderError(
            f"{spec.section_id}: schema_id is {declared!r}, expected "
            f"{spec.schema_id!r}"
        )
    status = raw.get("artifact_status")
    if status == "invalid":
        raise BuilderError(
            f"{spec.section_id}: artifact_status is 'invalid'. The runner "
            "marked this section unfit, so it may not become a candidate."
        )
    # The schema fixes each section's criterion, and the section title is
    # taken from the artifact rather than from this file, so a disagreement
    # has to be caught here or the candidate would carry the wrong heading.
    criterion = raw.get("criterion")
    if criterion != spec.criterion:
        raise BuilderError(
            f"{spec.section_id}: criterion is {criterion!r}, and its schema "
            f"requires {spec.criterion!r}"
        )
    return raw


def _sub_sections(spec: SectionSpec, raw: dict[str, Any]) -> list[dict[str, str]]:
    """The section's sub-sections, carried verbatim.

    Verbatim matters: the ids are the rubrics' anchors, and the anchor map
    fails closed on one that is absent.
    """
    subs = raw.get("sub_sections")
    if not isinstance(subs, list) or not subs:
        raise BuilderError(
            f"{spec.section_id}: sub_sections is empty or absent. The section's "
            "prose lives in its sub-sections and the rubrics anchor on their ids."
        )
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, sub in enumerate(subs):
        where = f"{spec.section_id}.sub_sections[{index}]"
        if not isinstance(sub, dict):
            raise BuilderError(f"{where}: must be an object")
        sub_id = sub.get("sub_section_id")
        if not isinstance(sub_id, str) or not sub_id.strip():
            raise BuilderError(f"{where}: sub_section_id is empty or absent")
        if sub_id in seen:
            raise BuilderError(f"{where}: duplicate sub_section_id {sub_id!r}")
        seen.add(sub_id)
        content = sub.get("content")
        if not isinstance(content, str) or not content.strip():
            raise BuilderError(f"{where}: content is empty or absent")
        title = sub.get("title")
        if not isinstance(title, str) or not title.strip():
            raise BuilderError(f"{where}: title is empty or absent")
        out.append(
            {"sub_section_id": sub_id, "title": title, "content": content}
        )
    return out


def _claims(spec: SectionSpec, raw: dict[str, Any]) -> list[dict[str, Any]]:
    """The section's claim statuses, mapped onto the graph's claim shape.

    ``verified_span`` is always absent. A Tier 5 ``source_ref`` is a path plus
    an id, never an offset range, and inventing offsets would defeat the claim
    verifier that checks a span against real source text.
    """
    validation = raw.get("validation_status")
    if not isinstance(validation, dict):
        raise BuilderError(f"{spec.section_id}: validation_status must be an object")
    statuses = validation.get("claim_statuses") or []
    if not isinstance(statuses, list):
        raise BuilderError(
            f"{spec.section_id}: validation_status.claim_statuses must be a list"
        )
    out: list[dict[str, Any]] = []
    for index, entry in enumerate(statuses):
        where = f"{spec.section_id}.claim_statuses[{index}]"
        if not isinstance(entry, dict):
            raise BuilderError(f"{where}: must be an object")
        claim_id = entry.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise BuilderError(f"{where}: claim_id is empty or absent")
        status = entry.get("status")
        if status not in EVIDENCE_STRENGTH_BY_STATUS:
            raise BuilderError(
                f"{where}: status {status!r} is not one of "
                f"{sorted(EVIDENCE_STRENGTH_BY_STATUS)}"
            )
        summary = entry.get("claim_summary")
        out.append(
            {
                "claim_id": claim_id,
                "section_id": spec.section_id,
                "text": summary if isinstance(summary, str) else "",
                "evidence_strength": EVIDENCE_STRENGTH_BY_STATUS[status],
                "approval": CLAIM_APPROVAL,
            }
        )
    return out


def build_candidate(
    repo_root: Path,
    *,
    document_id: str,
    title: str | None = None,
) -> dict[str, Any]:
    """The candidate content for *document_id*, built from Phase 8's sections.

    Pure apart from reading the three artifacts. Carries no run id and no
    timestamp: a candidate is content addressed, so either would move its
    ``content_version`` on every rerun and make each rerun a new version.
    """
    root = Path(repo_root)
    if not isinstance(document_id, str) or not document_id.strip():
        raise BuilderError("document_id is empty or absent")

    sections: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    seen_claims: set[str] = set()
    for spec in SECTION_SPECS:
        raw = _read_section(root, spec)
        sections.append(
            {
                "section_id": spec.section_id,
                # The artifact's own criterion, checked against the schema in
                # _read_section, so this is a copy and not a restatement.
                "title": raw["criterion"],
                "content": "",
                # Left empty deliberately. The snapshot builder checks that an
                # addressed id exists, and a Tier 5 section's own references
                # are work package and milestone ids whose presence as graph
                # nodes is not guaranteed.
                "addresses": [],
                "sub_sections": _sub_sections(spec, raw),
            }
        )
        for claim in _claims(spec, raw):
            if claim["claim_id"] in seen_claims:
                raise BuilderError(
                    f"claim_id {claim['claim_id']!r} is declared by more than "
                    "one section; the importer rejects a duplicate"
                )
            seen_claims.add(claim["claim_id"])
            claims.append(claim)

    candidate = {
        "document_id": document_id,
        "title": title or document_id,
        "sections": sections,
        "claims": claims,
        # No Tier 5 field carries a commitment in the shape the graph wants.
        # milestone_refs and wp_table_refs are id lists with no text, so
        # turning one into a commitment would invent its content (F6).
        "commitments": [],
    }

    # Checked against the validator the importer itself runs, rather than
    # against a second copy of its rules here.  Identifier shape, duplicate
    # ids and the claim-to-section reference are all its to judge; a build
    # that would not import is a build that fails now, with the reason.
    try:
        normalise_candidate(candidate, "built candidate")
    except DevGraphError as exc:
        raise BuilderError(
            f"the built candidate would not import: {exc}"
        ) from exc

    # Returned in source form, not normalised form.  The importer derives
    # declared_status from its own evidence lookup and fills verified_span,
    # and a candidate carrying those would be asserting what the graph infers.
    return candidate


def output_path(repo_root: Path, document_id: str) -> Path:
    """Absolute path of the candidate file for *document_id*."""
    return Path(repo_root) / CANDIDATES_REL / f"{document_id}.json"


def write_candidate(
    repo_root: Path,
    *,
    document_id: str,
    title: str | None = None,
) -> str:
    """Write the candidate atomically and return its path relative to the root.

    The only writer. ``main`` calls this rather than repeating the
    serialisation, so the path the CLI takes is the path the tests drive.
    ``atomic_write_json`` is the repo's canonical serialiser, so a crash
    mid-write leaves no half-written candidate and ``--check`` compares
    against the same bytes this function produces.
    """
    root = Path(repo_root).resolve()
    candidate = build_candidate(root, document_id=document_id, title=title)
    target = output_path(root, document_id)
    atomic_write_json(candidate, target)
    return target.relative_to(root).as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a blind-lane candidate document from Phase 8's Tier 5 "
            "section artifacts. Writes the candidate; does not import it."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_HERE.parent,
        help="Repository root (default: the root this tool lives in).",
    )
    parser.add_argument(
        "--document-id",
        default="DEMO-BIODIV-2027_part_b",
        help=(
            "Document id for the candidate. The default is the id the demo's "
            "blind-baseline validation report records as Assumed."
        ),
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Document title (default: the document id).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; exit 1 if the candidate on disk would change.",
    )
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()

    try:
        candidate = build_candidate(
            root, document_id=args.document_id, title=args.title
        )
    except BuilderError as exc:
        # Exit 2, on stderr, matching tools/derive_run_phase_costs.py: a
        # structural refusal is not the same event as --check drift, and a
        # caller must be able to tell them apart.
        print(f"[BLOCKED] {exc}", file=sys.stderr)
        return 2

    target = output_path(root, args.document_id)

    if args.check:
        expected = canonical_json_bytes(candidate)
        if not target.is_file():
            print(f"[DIFFERS] {target} does not exist.", file=sys.stderr)
            return 1
        if target.read_bytes() != expected:
            print(f"[DIFFERS] {target} would change.", file=sys.stderr)
            return 1
        print(f"[UNCHANGED] {target}")
        return 0

    rel = write_candidate(
        root, document_id=args.document_id, title=args.title
    )
    print(f"Wrote {rel}")
    for section in candidate["sections"]:
        ids = ", ".join(s["sub_section_id"] for s in section["sub_sections"])
        print(f"  {section['section_id']}: {ids}")
    print(
        f"  claims: {len(candidate['claims'])}  "
        f"commitments: {len(candidate['commitments'])}"
    )
    print(
        "Importing it is a separate act: "
        "runner.dev_graph.import_document(repo_root, rel)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
