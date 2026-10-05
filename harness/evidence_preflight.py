"""
Evidence preflight — what the blind assessor will see, before it sees it.

The blind lane selects evidence deterministically: for every rubric and every
section its criterion maps to, :func:`~harness.evidence_pack.build_evidence_pack`
keeps the paragraphs and claims that bear on the expectation and drops the
rest, either as ``not_relevant`` (no selection term matched) or as
``over_budget`` (relevant, but the token budget was spent).  Those drops decide
what the assessor reads.  The candidate hash, the profile version and the policy
version do not cover them: the budgets arrive as command-line flags, and the
demo recorded a case (finding F9, 2026-10-02) where a provider's rate-limit
ceiling fixed the pack budget and so predetermined every grade.

This module makes the selection visible and binds it.  It runs no assessor.

What it reports, in one record:

1. **Anchors present** against the rubrics the profile declares.  A declared
   anchor absent from the candidate is reported here instead of raising inside
   the assessor loop.
2. **``not_relevant`` exclusions** per expectation, with their token cost.
   This exclusion never flips a pack to ``insufficient_context``, so it is
   visible nowhere else.
3. **``over_budget`` exclusions** per expectation, with their token cost and
   the pack status they produced.
4. **Table rendering and row-parse counts** over the candidate's rendered
   pipe-delimited rows, against the import manifest when one exists.
5. **Package completeness** under the dev-graph package budget.
6. **The leakage scan**: the package guard, the snapshot's input list against
   every ``esr`` directory on disk (the historical evaluation is never
   snapshotted), and the instance-one word scan over the graph root.
7. **The pins**: candidate, profile, rubric set, scorecard, appendix mapping,
   policy, snapshot and package, **and** every input that selects evidence.

The binding is the **pack-set hash**: a canonical hash over the realised packs
— each pack's selection record and the exact text it renders for the assessor
— plus each criterion input's hash.  The packs are deterministic in every
selection input, so a change to any of them that changes what the assessor
sees moves the hash, whether or not anyone listed that input.  The parameter
values travel beside the hash, because a bare mismatch does not say what moved;
:func:`check_preflight` names every field that did.

The hash is a hash of an output.  It cannot tell two extraction or
normalisation versions apart when they happen to produce byte-identical packs,
so the import manifest — which carries those versions — is pinned separately
by its own sha256 and re-bound alongside.

``assess`` requires a preflight report and refuses on mismatch
(:class:`PreflightMismatch`).  The harness stays advisory to the pipeline; the
preflight is mandatory to the operator.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA; reads candidate artifacts and
    dev-graph records read-only and writes only harness-owned report files.
    Never a runtime gate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from runner.atomic_write import atomic_write_json
from runner.dev_graph import HISTORICAL_FEEDBACK_TAGS, build_snapshot
from runner.external_proposal import ExtractionError, is_row, parse_row
from runner.leakage_scan import scan_tree
from harness.blind_assessment import (
    EVIDENCE_SOURCE_DEV_GRAPH,
    EVIDENCE_SOURCE_DIRECTORY,
    LEAKAGE_FORBIDDEN_TYPES,
    BlindAssessmentError,
    BlindEvidence,
    Candidate,
    Clock,
    LeakageError,
    assert_no_leakage,
    candidate_hash,
    load_candidate,
    next_report_path,
)
from harness.criterion_scoring import CriterionInput, build_criterion_input
from harness.evidence_pack import (
    EXCLUDED_NOT_RELEVANT,
    EXCLUDED_OVER_BUDGET,
    KIND_CLAIM,
    KIND_PROSE_SPAN,
    PACK_INSUFFICIENT_CONTEXT,
    EvidencePack,
    split_paragraphs,
)
from harness.profile import canonical_hash
from harness.rubrics import ProfileBundle, build_pack_for

__all__ = [
    "PREFLIGHT_RECORD_TYPE",
    "PREFLIGHT_METRIC",
    "NOT_APPLICABLE",
    "ESR_SEGMENT",
    "IMPORT_MANIFESTS_REL",
    "PreflightMismatch",
    "PackParams",
    "RealisedPack",
    "RealisedPackSet",
    "realise_pack_set",
    "PreflightReport",
    "run_preflight",
    "write_preflight",
    "load_preflight",
    "check_preflight",
    "render_preflight",
    "file_sha256",
    "resolve_import_manifest",
]

#: The ``record_type`` of a persisted preflight report.
PREFLIGHT_RECORD_TYPE: str = "evidence_preflight_report"

#: The metric name stamped on the report.
PREFLIGHT_METRIC: str = "evidence_preflight"

#: A section of the report that the evidence route cannot answer: the
#: directory route carries no package, so package and leakage read this.
NOT_APPLICABLE: str = "not_applicable"

#: The path segment under which the historical evaluation record lives.  No
#: snapshot input may lie under a directory of this name (spec decision 12).
ESR_SEGMENT: str = "esr"

#: Where an external import leaves its manifest, relative to the graph root.
#: Mirrors the importer's own constant; the harness cannot import ``tools``.
IMPORT_MANIFESTS_REL: str = "docs/tier4_orchestration_state/dev_graph/imports"

#: File-name prefix for persisted preflight reports.
_REPORT_PREFIX: str = "preflight"

#: The advisory boundary sentence stamped on every preflight report.
_ADVISORY_NOTE: str = (
    "Advisory to a human, never run-blocking. The pack-set hash binds the "
    "evidence the blind assessor would read under exactly these parameters; "
    "assess requires it and refuses when the realised packs, the candidate, the "
    "profile or any selection parameter moved (see harness/HARNESS.md)."
)

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path | str) -> str:
    """The plain hex sha256 of a file's bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PreflightMismatch(BlindAssessmentError):
    """The preflight on disk does not describe the evidence about to be assessed."""


# --------------------------------------------------------------------------- #
# Parameters and the realised pack set
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PackParams:
    """Every command-line input that selects evidence.

    The rubric set carries the terms and anchors; these are the rest.  They are
    reported beside the pack-set hash so a mismatch can be explained.
    """

    token_budget: int
    span_budget_fraction: float
    max_token_budget: int | None
    include_claims: bool
    criterion_token_budget: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_budget": self.token_budget,
            "span_budget_fraction": self.span_budget_fraction,
            "max_token_budget": self.max_token_budget,
            "include_claims": self.include_claims,
            "criterion_token_budget": self.criterion_token_budget,
        }


def _sub_section_ids(section: Any) -> list[str]:
    subs = section.get("sub_sections") if isinstance(section, Mapping) else None
    if not isinstance(subs, list):
        return []
    return [str(s.get("sub_section_id")) for s in subs if isinstance(s, Mapping)]


@dataclass(frozen=True)
class RealisedPack:
    """One ``(expectation, section)`` pack as the blind lane would build it.

    ``pack`` is ``None`` when the section is missing from the candidate or a
    declared anchor is absent from it; the reason is recorded rather than
    raised, so the report can name it.  ``hash`` is the canonical hash of
    :attr:`binding_record`.
    """

    expectation_key: str
    criterion_id: str
    section_id: str
    pack: EvidencePack | None
    missing_anchors: tuple[str, ...] = ()
    section_missing: bool = False

    @property
    def reason(self) -> str:
        """Why no pack was built: ``section_missing`` or ``anchor_missing``; empty when one was."""
        if self.pack is not None:
            return ""
        return "section_missing" if self.section_missing else "anchor_missing"

    @property
    def binding_record(self) -> dict[str, Any]:
        """What the hash covers: the selection record without its machine
        path, plus the exact text the assessor would read."""
        if self.pack is None:
            return {
                "expectation_key": self.expectation_key,
                "section_id": self.section_id,
                "error": self.reason,
                "missing_anchors": list(self.missing_anchors),
            }
        record = self.pack.to_dict()
        record.pop("section_path", None)
        record["rendered"] = self.pack.render()
        return record

    @property
    def hash(self) -> str:
        return canonical_hash(self.binding_record)

    def _excluded(self, reason: str) -> dict[str, int]:
        items = [e for e in (self.pack.excluded if self.pack else ()) if e.reason == reason]
        return {
            "spans": sum(1 for e in items if e.kind == KIND_PROSE_SPAN),
            "claims": sum(1 for e in items if e.kind == KIND_CLAIM),
            "tokens": sum(e.token_estimate for e in items),
        }

    def to_dict(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "expectation_key": self.expectation_key,
            "criterion_id": self.criterion_id,
            "section_id": self.section_id,
            "hash": self.hash,
        }
        if self.pack is None:
            base.update(
                {
                    "status": "not_built",
                    "reason": self.reason,
                    "missing_anchors": list(self.missing_anchors),
                }
            )
            return base
        pack = self.pack
        base.update(
            {
                "status": pack.status,
                "token_budget": pack.token_budget,
                "token_estimate": pack.token_estimate,
                "include_claims": pack.include_claims,
                "anchor_sub_section_ids": list(pack.anchor_sub_section_ids),
                "included": {
                    "spans": len(pack.spans),
                    "claims": len(pack.claims),
                    "tokens": sum(s.token_estimate for s in pack.spans)
                    + sum(c.token_estimate for c in pack.claims),
                },
                EXCLUDED_NOT_RELEVANT: self._excluded(EXCLUDED_NOT_RELEVANT),
                EXCLUDED_OVER_BUDGET: self._excluded(EXCLUDED_OVER_BUDGET),
            }
        )
        return base


@dataclass(frozen=True)
class RealisedPackSet:
    """Every pack and criterion input the blind lane would build, and their hash."""

    packs: tuple[RealisedPack, ...]
    criterion_inputs: tuple[CriterionInput, ...]
    params: PackParams

    @property
    def hash(self) -> str:
        """Canonical over the per-pack hashes, the criterion inputs and the parameters.

        The parameters are inside the hash as well as beside it: a ceiling or a span
        fraction that happens to select the same text must still move the hash, because
        the frozen blind report binds this hash alone (spec PE-06) and finding F9 was
        exactly a ceiling nobody recorded.
        """
        return canonical_hash(
            {
                "params": self.params.to_dict(),
                "packs": {f"{p.expectation_key}/{p.section_id}": p.hash for p in self.packs},
                "criteria": {
                    c.criterion_id: {
                        "input_hash": c.input_hash,
                        "token_budget": c.token_budget,
                        "complete": c.complete,
                        "incompleteness": list(c.incompleteness),
                    }
                    for c in self.criterion_inputs
                },
            }
        )


def realise_pack_set(bundle: ProfileBundle, candidate: Candidate, params: PackParams) -> RealisedPackSet:
    """Build every pack and criterion input exactly as ``assess_candidate`` would.

    Same rubric order, same section map, same
    :func:`~harness.rubrics.build_pack_for` binding.  A missing section or a
    missing anchor yields a :class:`RealisedPack` without a pack rather than an
    exception, so the preflight can report it; an unusable section artifact
    still raises :class:`~harness.evidence_pack.EvidencePackError`.
    """
    packs: list[RealisedPack] = []
    for rubric in bundle.rubric_set.rubrics:
        for section_id in bundle.profile.section_ids_for(rubric.criterion_id):
            path = candidate.sections.get(section_id)
            if path is None:
                packs.append(
                    RealisedPack(rubric.expectation_key, rubric.criterion_id, section_id, None, section_missing=True)
                )
                continue
            known = set(_sub_section_ids(candidate.contents[section_id]))
            missing = tuple(a for a in rubric.anchor_sub_section_ids if a not in known)
            if missing:
                packs.append(
                    RealisedPack(rubric.expectation_key, rubric.criterion_id, section_id, None, missing_anchors=missing)
                )
                continue
            pack = build_pack_for(
                rubric,
                path,
                token_budget=params.token_budget,
                span_budget_fraction=params.span_budget_fraction,
                max_token_budget=params.max_token_budget,
                include_claims=params.include_claims,
            )
            packs.append(RealisedPack(rubric.expectation_key, rubric.criterion_id, section_id, pack))
    inputs = tuple(
        build_criterion_input(bundle, candidate, cid, token_budget=params.criterion_token_budget)
        for cid in bundle.profile.criterion_ids
    )
    return RealisedPackSet(packs=tuple(packs), criterion_inputs=inputs, params=params)


# --------------------------------------------------------------------------- #
# The seven sections
# --------------------------------------------------------------------------- #


def _anchors_section(bundle: ProfileBundle, realised: RealisedPackSet) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    complete = 0
    for p in realised.packs:
        rubric = next(r for r in bundle.rubric_set.rubrics if r.expectation_key == p.expectation_key)
        present = [a for a in rubric.anchor_sub_section_ids if a not in p.missing_anchors] if not p.section_missing else []
        rows.append(
            {
                "expectation_key": p.expectation_key,
                "criterion_id": p.criterion_id,
                "section_id": p.section_id,
                "section_present": not p.section_missing,
                "anchors": list(rubric.anchor_sub_section_ids),
                "present": present,
                "missing": list(p.missing_anchors) if not p.section_missing else list(rubric.anchor_sub_section_ids),
            }
        )
        if p.pack is not None:
            complete += 1
        elif p.missing_anchors:
            missing.append(
                {"expectation_key": p.expectation_key, "section_id": p.section_id, "anchors": list(p.missing_anchors)}
            )
    return {
        "declared_rubrics": len(realised.packs),
        "rubrics_with_every_anchor_present": complete,
        "missing": missing,
        "rubrics": rows,
    }


def _exclusion_totals(realised: RealisedPackSet) -> dict[str, dict[str, int]]:
    totals = {
        EXCLUDED_NOT_RELEVANT: {"items": 0, "tokens": 0},
        EXCLUDED_OVER_BUDGET: {"items": 0, "tokens": 0},
    }
    for p in realised.packs:
        for e in (p.pack.excluded if p.pack else ()):
            if e.reason in totals:
                totals[e.reason]["items"] += 1
                totals[e.reason]["tokens"] += e.token_estimate
    return totals


def _tables_section(candidate: Candidate, manifest: Mapping[str, Any] | None) -> dict[str, Any]:
    per_section: dict[str, dict[str, int]] = {}
    rendered = parsed = cells = 0
    unparsed: list[str] = []
    for sid in sorted(candidate.contents):
        section = candidate.contents[sid]
        counts = {"rows_rendered": 0, "rows_parsed": 0, "cells": 0}
        subs = section.get("sub_sections") if isinstance(section, Mapping) else None
        for sub in subs if isinstance(subs, list) else []:
            content = str(sub.get("content", "")) if isinstance(sub, Mapping) else ""
            for paragraph in split_paragraphs(content):
                if not is_row(paragraph):
                    continue
                counts["rows_rendered"] += 1
                try:
                    row = parse_row(paragraph)
                except ExtractionError:
                    unparsed.append(f"{sid}: {paragraph[:60]}")
                    continue
                counts["rows_parsed"] += 1
                counts["cells"] += len(row)
        per_section[sid] = counts
        rendered += counts["rows_rendered"]
        parsed += counts["rows_parsed"]
        cells += counts["cells"]
    declared: dict[str, Any] | None = None
    agrees: bool | None = None
    tables = manifest.get("tables") if isinstance(manifest, Mapping) else None
    if isinstance(tables, Mapping):
        declared = {
            k: tables.get(k) for k in ("count", "rows_rendered", "rows_parsed") if k in tables
        }
        agrees = declared.get("rows_rendered") == rendered and declared.get("rows_parsed") == parsed
    return {
        "rows_rendered": rendered,
        "rows_parsed": parsed,
        "rows_unparsed": unparsed,
        "cells": cells,
        "per_section": per_section,
        "manifest": declared,
        "agrees_with_manifest": agrees,
    }


def _package_section(evidence: BlindEvidence) -> dict[str, Any]:
    manifest = evidence.package.manifest
    by_reason: dict[str, int] = {}
    for e in manifest.get("exclusions", []):
        by_reason[str(e.get("reason"))] = by_reason.get(str(e.get("reason")), 0) + 1
    return {
        "budget": manifest.get("budget"),
        "completeness": manifest.get("completeness"),
        "included": len(evidence.package.items),
        "exclusions": dict(sorted(by_reason.items())),
        "unresolved": len(manifest.get("unresolved", [])),
        "worst_declared_status": manifest.get("worst_declared_status"),
    }


def _esr_directories(root: Path) -> list[Path]:
    """Every directory named :data:`ESR_SEGMENT` under *root*'s Tier 4, sorted."""
    tier4 = root / "docs" / "tier4_orchestration_state"
    if not tier4.is_dir():
        return []
    found: list[Path] = []
    for dirpath, dirnames, _files in os.walk(tier4):
        for d in dirnames:
            if d == ESR_SEGMENT:
                found.append(Path(dirpath) / d)
    return sorted(found)


def _esr_section(graph_root: Path, repo_root: Path) -> dict[str, Any]:
    snapshot = build_snapshot(graph_root)
    inputs = list(snapshot.inputs)
    under_esr = [p for p in inputs if ESR_SEGMENT in Path(p).parts]
    graph_resolved = graph_root.resolve()
    directories: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for base in (graph_root, repo_root):
        for esr_dir in _esr_directories(base):
            resolved = esr_dir.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                rel_graph = resolved.relative_to(graph_resolved).as_posix()
                under_graph = True
            except ValueError:
                rel_graph = ""
                under_graph = False
            read = under_graph and any(p == rel_graph or p.startswith(rel_graph + "/") for p in inputs)
            directories.append(
                {
                    "path": esr_dir.relative_to(base).as_posix(),
                    "under_graph_root": under_graph,
                    "read_by_snapshot": read,
                }
            )
    directories.sort(key=lambda d: d["path"])
    return {
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_inputs": len(inputs),
        "inputs_under_esr": under_esr,
        "esr_directories": directories,
        "never_snapshotted": not under_esr and not any(d["read_by_snapshot"] for d in directories),
    }


def _leakage_section(evidence: BlindEvidence, graph_root: Path, repo_root: Path) -> dict[str, Any]:
    guard: dict[str, Any] = {
        "view": evidence.package.manifest.get("view"),
        "forbidden_types": sorted(LEAKAGE_FORBIDDEN_TYPES),
        "forbidden_tags": sorted(HISTORICAL_FEEDBACK_TAGS),
        "items_checked": len(evidence.package.items),
    }
    try:
        assert_no_leakage(evidence.package)
        guard["passed"] = True
    except LeakageError as exc:
        guard["passed"] = False
        guard["error"] = str(exc)
    scan = scan_tree(graph_root)
    word_scan = {
        "root": "graph_root",
        "files_scanned": len(scan.scanned_files),
        "ok": scan.ok,
        "clean": scan.clean,
        "new_violations": len(scan.new_violations),
        "pre_existing_violations": len(scan.pre_existing_violations),
        "violations": [
            {"path": v.path, "line": v.line, "noun": v.noun, "pre_existing": v.pre_existing}
            for v in scan.violations[:50]
        ],
    }
    return {"guard": guard, "esr": _esr_section(graph_root, repo_root), "word_scan": word_scan}


def _manifest_pin(path: Path, display: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise BlindAssessmentError(f"import manifest {path} is not valid JSON: {exc}") from exc
    versions = data.get("versions") if isinstance(data, Mapping) else None
    return {
        "path": display,
        "sha256": file_sha256(path),
        "record_type": data.get("record_type") if isinstance(data, Mapping) else None,
        "versions": dict(versions) if isinstance(versions, Mapping) else {},
        "_data": data,
    }


def resolve_import_manifest(
    import_manifest: Path | str | None, evidence: BlindEvidence | None, graph_root: Path | None
) -> tuple[Path, str] | None:
    if import_manifest is not None:
        p = Path(import_manifest)
        if not p.is_file():
            raise BlindAssessmentError(f"import manifest not found: {p}")
        return p, p.as_posix()
    if evidence is None or graph_root is None:
        return None
    rel = f"{IMPORT_MANIFESTS_REL}/{evidence.document_id}.json"
    p = graph_root / rel
    return (p, rel) if p.is_file() else None


# --------------------------------------------------------------------------- #
# The report
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PreflightReport:
    """The preflight of one candidate under one parameter set — bound, advisory."""

    candidate_hash: str
    candidate_path: str
    evidence_source: str
    profile_id: str
    profile_version: str
    rubric_set_id: str
    rubric_set_version: str
    rubric_set_fingerprint: str
    scorecard_id: str
    scorecard_version: str
    scorecard_hash: str
    appendix_mapping: Mapping[str, Any] | None
    params: PackParams
    pack_set_hash: str
    preflight_at: str
    anchors: Mapping[str, Any]
    packs: tuple[Mapping[str, Any], ...]
    exclusions: Mapping[str, Mapping[str, int]]
    criterion_inputs: tuple[Mapping[str, Any], ...]
    tables: Mapping[str, Any]
    package: Mapping[str, Any] | str
    leakage: Mapping[str, Any] | str
    import_manifest: Mapping[str, Any] | None
    flags: tuple[str, ...]
    document: str = ""
    document_id: str = ""
    snapshot_id: str = ""
    package_id: str = ""
    policy_version: str = ""
    evidence_view: str = ""
    notes: str = _ADVISORY_NOTE
    advisory: bool = True
    blocking: bool = False

    def __post_init__(self) -> None:
        if self.advisory is not True or self.blocking is not False:
            raise ValueError("PreflightReport must carry advisory=True and blocking=False.")
        if not str(self.candidate_hash).startswith("sha256:"):
            raise ValueError("PreflightReport.candidate_hash must be a sha256: hash.")
        if self.evidence_source not in (EVIDENCE_SOURCE_DEV_GRAPH, EVIDENCE_SOURCE_DIRECTORY):
            raise ValueError(f"unknown evidence_source {self.evidence_source!r}.")

    def to_dict(self) -> dict[str, Any]:
        manifest = None
        if self.import_manifest is not None:
            manifest = {k: v for k, v in self.import_manifest.items() if k != "_data"}
        return {
            "record_type": PREFLIGHT_RECORD_TYPE,
            "metric": PREFLIGHT_METRIC,
            "advisory": self.advisory,
            "blocking": self.blocking,
            "preflight_at": self.preflight_at,
            "candidate_hash": self.candidate_hash,
            "candidate_path": self.candidate_path,
            "evidence_source": self.evidence_source,
            "document": self.document,
            "document_id": self.document_id,
            "snapshot_id": self.snapshot_id,
            "package_id": self.package_id,
            "policy_version": self.policy_version,
            "evidence_view": self.evidence_view,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "rubric_set_id": self.rubric_set_id,
            "rubric_set_version": self.rubric_set_version,
            "rubric_set_fingerprint": self.rubric_set_fingerprint,
            "scorecard_id": self.scorecard_id,
            "scorecard_version": self.scorecard_version,
            "scorecard_hash": self.scorecard_hash,
            "appendix_mapping": dict(self.appendix_mapping) if self.appendix_mapping else None,
            "params": self.params.to_dict(),
            "pack_set_hash": self.pack_set_hash,
            "import_manifest": manifest,
            "anchors": dict(self.anchors),
            "packs": [dict(p) for p in self.packs],
            "exclusions": {k: dict(v) for k, v in self.exclusions.items()},
            "criterion_inputs": [dict(c) for c in self.criterion_inputs],
            "tables": dict(self.tables),
            "package": dict(self.package) if isinstance(self.package, Mapping) else self.package,
            "leakage": dict(self.leakage) if isinstance(self.leakage, Mapping) else self.leakage,
            "flags": list(self.flags),
            "notes": self.notes,
        }


def _criterion_record(c: CriterionInput) -> dict[str, Any]:
    return {
        "criterion_id": c.criterion_id,
        "section_ids": list(c.section_ids),
        "present_section_ids": list(c.present_section_ids),
        "input_hash": c.input_hash,
        "section_hash": c.section_hash,
        "token_estimate": c.token_estimate,
        "token_budget": c.token_budget,
        "complete": c.complete,
        "incompleteness": list(c.incompleteness),
        "appendix_rows": len(c.appendix),
    }


def _flags(
    realised: RealisedPackSet,
    candidate: Candidate,
    tables: Mapping[str, Any],
    package: Mapping[str, Any] | str,
    leakage: Mapping[str, Any] | str,
) -> tuple[str, ...]:
    flags: list[str] = []
    if candidate.missing:
        flags.append(
            f"{len(candidate.missing)} required section(s) missing from the candidate: "
            + ", ".join(m.section_id for m in candidate.missing)
        )
    anchor_missing = [p for p in realised.packs if p.missing_anchors]
    if anchor_missing:
        flags.append(
            f"{len(anchor_missing)} rubric(s) with a declared anchor absent from the candidate: "
            + ", ".join(f"{p.expectation_key}/{p.section_id} {list(p.missing_anchors)}" for p in anchor_missing)
        )
    truncated = [p for p in realised.packs if p.pack is not None and p.pack.status == PACK_INSUFFICIENT_CONTEXT]
    if truncated:
        flags.append(
            f"{len(truncated)} pack(s) {PACK_INSUFFICIENT_CONTEXT} (relevant evidence over budget): "
            + ", ".join(f"{p.expectation_key}/{p.section_id}" for p in truncated)
        )
    incomplete = [c for c in realised.criterion_inputs if not c.complete]
    if incomplete:
        flags.append(
            f"{len(incomplete)} criterion input(s) incomplete: "
            + "; ".join(f"{c.criterion_id}: {' / '.join(c.incompleteness)}" for c in incomplete)
        )
    if tables.get("rows_unparsed"):
        flags.append(f"{len(tables['rows_unparsed'])} rendered table row(s) failed to parse")
    if tables.get("agrees_with_manifest") is False:
        flags.append(
            f"table rows disagree with the import manifest: candidate {tables['rows_rendered']}/"
            f"{tables['rows_parsed']} rendered/parsed, manifest {tables['manifest']}"
        )
    if isinstance(package, Mapping) and package.get("completeness") != "complete":
        flags.append(f"package {package.get('completeness')} under budget {package.get('budget')}")
    if isinstance(leakage, Mapping):
        if not leakage["guard"].get("passed"):
            flags.append(f"leakage guard failed: {leakage['guard'].get('error')}")
        if not leakage["esr"].get("never_snapshotted"):
            flags.append("the snapshot read an esr directory")
        if not leakage["word_scan"].get("ok"):
            flags.append(f"word scan: {leakage['word_scan']['new_violations']} new instance-one leak(s)")
    return tuple(flags)


def run_preflight(
    bundle: ProfileBundle,
    *,
    candidate_dir: Path | str | None = None,
    evidence: BlindEvidence | None = None,
    params: PackParams,
    graph_root: Path | str | None = None,
    repo_root: Path | str | None = None,
    import_manifest: Path | str | None = None,
    clock: Clock | None = None,
) -> PreflightReport:
    """Realise the pack set and report the seven things; run no assessor.

    Exactly one of *candidate_dir* and *evidence* is given, as for
    ``assess_candidate``.  The package and leakage sections need *evidence*
    and *graph_root*; without a package they read :data:`NOT_APPLICABLE`.
    The import manifest is pinned when given, or found at
    ``<graph_root>/<IMPORT_MANIFESTS_REL>/<document_id>.json``.
    """
    if evidence is not None and candidate_dir is None:
        source: Path | str = evidence.candidate_dir
    elif candidate_dir is not None and evidence is None:
        source = candidate_dir
    else:
        raise BlindAssessmentError("give exactly one of candidate_dir or evidence.")
    candidate = load_candidate(source, bundle.profile)
    realised = realise_pack_set(bundle, candidate, params)
    groot = Path(graph_root) if graph_root is not None else None
    rroot = Path(repo_root) if repo_root is not None else (groot or Path("."))
    manifest_pin: dict[str, Any] | None = None
    resolved = resolve_import_manifest(import_manifest, evidence, groot)
    if resolved is not None:
        manifest_pin = _manifest_pin(*resolved)
    tables = _tables_section(candidate, manifest_pin["_data"] if manifest_pin else None)
    package: Mapping[str, Any] | str = NOT_APPLICABLE
    leakage: Mapping[str, Any] | str = NOT_APPLICABLE
    if evidence is not None:
        package = _package_section(evidence)
        if groot is None:
            raise BlindAssessmentError("the document route needs graph_root for the leakage section.")
        leakage = _leakage_section(evidence, groot, rroot)
    mapping = bundle.appendix_mapping
    rubric_set = bundle.rubric_set
    return PreflightReport(
        candidate_hash=candidate_hash(candidate),
        candidate_path=candidate.root.as_posix(),
        evidence_source=EVIDENCE_SOURCE_DEV_GRAPH if evidence is not None else EVIDENCE_SOURCE_DIRECTORY,
        profile_id=bundle.profile_id,
        profile_version=bundle.version,
        rubric_set_id=rubric_set.rubric_set_id,
        rubric_set_version=rubric_set.version,
        rubric_set_fingerprint=rubric_set.fingerprint,
        scorecard_id=rubric_set.scorecard_id,
        scorecard_version=rubric_set.scorecard_version,
        scorecard_hash=bundle.scorecard_hash,
        appendix_mapping=(
            {"mapping_id": mapping.mapping_id, "path": mapping.path, "sha256": mapping.sha256}
            if mapping is not None
            else None
        ),
        params=params,
        pack_set_hash=realised.hash,
        preflight_at=(clock or _utc_now)(),
        anchors=_anchors_section(bundle, realised),
        packs=tuple(p.to_dict() for p in realised.packs),
        exclusions=_exclusion_totals(realised),
        criterion_inputs=tuple(_criterion_record(c) for c in realised.criterion_inputs),
        tables=tables,
        package=package,
        leakage=leakage,
        import_manifest=manifest_pin,
        flags=_flags(realised, candidate, tables, package, leakage),
        document=evidence.document if evidence is not None else "",
        document_id=evidence.document_id if evidence is not None else "",
        snapshot_id=evidence.snapshot_id if evidence is not None else "",
        package_id=evidence.package.package_id if evidence is not None else "",
        policy_version=str(evidence.package.manifest.get("policy_version", "")) if evidence is not None else "",
        evidence_view=str(evidence.package.manifest.get("view", "")) if evidence is not None else "",
    )


# --------------------------------------------------------------------------- #
# Persistence and re-binding
# --------------------------------------------------------------------------- #


def write_preflight(report: PreflightReport, reports_dir: Path | str) -> Path:
    """Write *report* as ``preflight_<hash12>_<NNNN>.json``; never overwrite."""
    out_dir = Path(reports_dir)
    target = next_report_path(out_dir, report.candidate_hash, prefix=_REPORT_PREFIX)
    out_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(report.to_dict(), target, prefix="evidence_preflight_")
    return target


def load_preflight(path: Path | str) -> dict[str, Any]:
    """Load a persisted preflight report, fail-closed on shape and flags."""
    p = Path(path)
    if not p.is_file():
        raise BlindAssessmentError(f"preflight report not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise BlindAssessmentError(f"preflight {p} is not valid JSON: {exc}") from exc
    if not isinstance(data, Mapping) or data.get("record_type") != PREFLIGHT_RECORD_TYPE:
        raise BlindAssessmentError(f"{p} is not an {PREFLIGHT_RECORD_TYPE!r} record.")
    if data.get("advisory") is not True or data.get("blocking") is not False:
        raise BlindAssessmentError(f"preflight {p} must carry advisory=true and blocking=false.")
    for key in ("candidate_hash", "profile_version", "rubric_set_fingerprint", "pack_set_hash", "params", "packs"):
        if key not in data:
            raise BlindAssessmentError(f"preflight {p} lacks {key!r}.")
    return dict(data)


def check_preflight(
    data: Mapping[str, Any],
    *,
    bundle: ProfileBundle,
    candidate: Candidate,
    realised: RealisedPackSet,
    params: PackParams,
    import_manifest_sha256: str | None = None,
    evidence: BlindEvidence | None = None,
) -> str:
    """Re-bind a loaded preflight to what is about to be assessed.

    Returns the pack-set hash when the preflight describes exactly this
    candidate, profile, parameter set and realised pack set (and the same
    import manifest, when the preflight pinned one, and the same snapshot, package
    and policy, when *evidence* is given).  Otherwise raises
    :class:`PreflightMismatch` naming **every** field that moved, pack by pack.
    """
    moved: list[str] = []

    def _cmp(field: str, then: Any, now: Any) -> None:
        if then != now:
            moved.append(f"{field}: preflight {then!r}, now {now!r}")

    _cmp("candidate_hash", data.get("candidate_hash"), candidate_hash(candidate))
    _cmp("profile_id", data.get("profile_id"), bundle.profile_id)
    _cmp("profile_version", data.get("profile_version"), bundle.version)
    _cmp("rubric_set_fingerprint", data.get("rubric_set_fingerprint"), bundle.rubric_set.fingerprint)
    raw_params = data.get("params")
    then_params: Mapping[str, Any] = raw_params if isinstance(raw_params, Mapping) else {}
    for key, now in params.to_dict().items():
        _cmp(f"params.{key}", then_params.get(key), now)
    if evidence is not None:
        _cmp("snapshot_id", data.get("snapshot_id"), evidence.snapshot_id)
        _cmp("package_id", data.get("package_id"), evidence.package.package_id)
        _cmp("policy_version", data.get("policy_version"), str(evidence.package.manifest.get("policy_version", "")))
    pinned = data.get("import_manifest")
    if isinstance(pinned, Mapping) and pinned.get("sha256"):
        _cmp("import_manifest.sha256", pinned.get("sha256"), import_manifest_sha256)
    then_packs = {
        f"{p.get('expectation_key')}/{p.get('section_id')}": p.get("hash")
        for p in data.get("packs", [])
        if isinstance(p, Mapping)
    }
    now_packs = {f"{p.expectation_key}/{p.section_id}": p.hash for p in realised.packs}
    for key in sorted(set(then_packs) | set(now_packs)):
        if then_packs.get(key) != now_packs.get(key):
            moved.append(
                f"pack {key}: preflight {str(then_packs.get(key))[:19]}, now {str(now_packs.get(key))[:19]}"
            )
    _cmp("pack_set_hash", data.get("pack_set_hash"), realised.hash)
    if moved:
        raise PreflightMismatch(
            "the preflight does not describe the evidence about to be assessed; "
            f"{len(moved)} field(s) moved:\n  - " + "\n  - ".join(moved)
            + "\nRe-run the preflight with the parameters you will assess with."
        )
    return str(data["pack_set_hash"])


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _ascii(text: str) -> str:
    return str(text).encode("ascii", "backslashreplace").decode("ascii")


def _table(rows: list[tuple[str, ...]]) -> list[str]:
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    lines = []
    for i, row in enumerate(rows):
        lines.append("  ".join(col.ljust(widths[j]) for j, col in enumerate(row)).rstrip())
        if i == 0:
            lines.append("  ".join("-" * w for w in widths))
    return lines


def render_preflight(report: Mapping[str, Any]) -> str:
    """Render a preflight dict (fresh ``to_dict()`` or a loaded file) as text."""
    flags = list(report.get("flags") or [])
    params = report.get("params") or {}
    lines = [
        f"EVIDENCE PREFLIGHT [{'FLAGGED' if flags else 'OK'}] - {len(report.get('packs') or [])} pack(s)",
        f"candidate: {str(report.get('candidate_hash') or '')[:19]}  {report.get('candidate_path', '')}",
        f"profile:   {report.get('profile_id', '') or '-'} [{str(report.get('profile_version') or '')[:19]}]  "
        f"rubrics {report.get('rubric_set_id', '-')} v{report.get('rubric_set_version', '-')}",
        f"pack set:  {str(report.get('pack_set_hash') or '')[:19]}  "
        + "  ".join(f"{k}={v}" for k, v in params.items()),
    ]
    if report.get("package_id"):
        lines.append(
            f"evidence:  source={report.get('evidence_source')} view={report.get('evidence_view')} "
            f"package={str(report.get('package_id') or '')[:19]} snapshot={str(report.get('snapshot_id') or '')[:19]}"
        )
    else:
        lines.append(f"evidence:  source={report.get('evidence_source')} (no dev-graph package)")
    manifest = report.get("import_manifest")
    if isinstance(manifest, Mapping):
        versions = "  ".join(f"{k}={v}" for k, v in (manifest.get("versions") or {}).items())
        lines.append(f"manifest:  sha256:{str(manifest.get('sha256'))[:12]}  {manifest.get('path')}  {versions}")
    anchors = report.get("anchors") or {}
    lines.append(
        f"\nANCHORS - {anchors.get('rubrics_with_every_anchor_present', 0)} of "
        f"{anchors.get('declared_rubrics', 0)} rubric(s) have every declared anchor present"
    )
    for m in anchors.get("missing") or []:
        lines.append(f"  - {m.get('expectation_key')}/{m.get('section_id')}: missing {m.get('anchors')}")
    lines.append("\nPACKS - what the assessor would read, and what was dropped")
    rows: list[tuple[str, ...]] = [
        ("expectation", "section", "status", "budget", "used", "incl spans/claims",
         "not_relevant (tok)", "over_budget (tok)")
    ]
    for p in report.get("packs") or []:
        if p.get("status") == "not_built":
            rows.append((str(p.get("expectation_key")), str(p.get("section_id")), f"not built: {p.get('reason')}",
                         "-", "-", "-", "-", "-"))
            continue
        inc = p.get("included") or {}
        nr = p.get(EXCLUDED_NOT_RELEVANT) or {}
        ob = p.get(EXCLUDED_OVER_BUDGET) or {}
        rows.append(
            (
                str(p.get("expectation_key")),
                str(p.get("section_id")),
                str(p.get("status")),
                str(p.get("token_budget")),
                str(p.get("token_estimate")),
                f"{inc.get('spans', 0)}/{inc.get('claims', 0)}",
                f"{nr.get('spans', 0)}+{nr.get('claims', 0)} ({nr.get('tokens', 0)})",
                f"{ob.get('spans', 0)}+{ob.get('claims', 0)} ({ob.get('tokens', 0)})",
            )
        )
    lines.extend(_table(rows))
    totals = report.get("exclusions") or {}
    lines.append(
        "exclusions: "
        + "  ".join(f"{k}: {v.get('items', 0)} item(s), {v.get('tokens', 0)} token(s)" for k, v in totals.items())
    )
    crit = report.get("criterion_inputs") or []
    if crit:
        lines.append("\nCRITERION INPUTS - complete section plus declared appendix")
        crows: list[tuple[str, ...]] = [("criterion", "input", "tokens", "budget", "complete")]
        for c in crit:
            crows.append((str(c.get("criterion_id")), str(c.get("input_hash") or "")[:19],
                          str(c.get("token_estimate")), str(c.get("token_budget")),
                          "yes" if c.get("complete") else "no"))
        lines.extend(_table(crows))
    tables = report.get("tables") or {}
    manifest_note = ""
    if tables.get("manifest") is not None:
        manifest_note = f"; manifest {tables['manifest']} agrees={tables.get('agrees_with_manifest')}"
    lines.append(
        f"\nTABLES - {tables.get('rows_rendered', 0)} row(s) rendered, {tables.get('rows_parsed', 0)} parsed, "
        f"{tables.get('cells', 0)} cell(s){manifest_note}"
    )
    package = report.get("package")
    if isinstance(package, Mapping):
        lines.append(
            f"PACKAGE - {package.get('completeness')} under budget {package.get('budget')}: "
            f"{package.get('included')} item(s) included, exclusions {package.get('exclusions')}, "
            f"{package.get('unresolved')} unresolved"
        )
    else:
        lines.append(f"PACKAGE - {package}")
    leakage = report.get("leakage")
    if isinstance(leakage, Mapping):
        guard, esr, scan = leakage.get("guard") or {}, leakage.get("esr") or {}, leakage.get("word_scan") or {}
        lines.append(
            f"LEAKAGE - guard {'passed' if guard.get('passed') else 'FAILED'} over {guard.get('items_checked')} item(s); "
            f"esr never snapshotted: {esr.get('never_snapshotted')} ({esr.get('snapshot_inputs')} snapshot input(s), "
            f"{len(esr.get('esr_directories') or [])} esr dir(s) on disk); "
            f"word scan over {scan.get('files_scanned')} file(s): {'ok' if scan.get('ok') else 'FAIL'}"
            f"{'' if scan.get('clean') else ' (not clean: pre-existing hits recorded)'}"
        )
    else:
        lines.append(f"LEAKAGE - {leakage}")
    if flags:
        lines.append("\nFLAGS - read before spending assessor quota:")
        lines.extend(f"  - {f}" for f in flags)
    else:
        lines.append("\nno flags")
    return _ascii("\n".join(lines))
