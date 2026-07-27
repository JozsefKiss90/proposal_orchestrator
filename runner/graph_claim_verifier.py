"""
Independent claim→node re-verification — the DOD-1b traceability auditor
(milestone 2, ticket 8.2).

The graph→docs compiler (:mod:`runner.graph_compiler`) turns ``proposal_section``
vault nodes into the Tier-5 ``{slug}_section.json`` deliverables, stamping each
sub-section's ``validation_status.claim_statuses[]`` with a ``claim_id`` (the node
id) and a ``status`` computed from the node's ``evidence_strength``.  Confirming
that the *published* sections trace back to the vault by **re-running the
compiler and diffing** would only prove the compiler is deterministic — not that
the committed deliverables are correct (DOD-1b: "confirm every Part B claim traces
to its vault node, **not merely that the compile ran**").

This module is the **independent** auditor.  It reads the committed section
artifacts from disk (never a fresh compile) and the vault (via the shared
:mod:`runner.vault_reader` substrate, **not** the compiler), and asserts the
traceability invariant directly:

* **claim_id ⊆ vault node ids.**  Every published ``claim_id`` is the id of a
  *bound* ``proposal_section`` vault node (the population the compiler draws from).
* **status is the Appendix-B map of the node's evidence.**  Every published
  claim ``status`` equals :data:`~runner.graph_schema.EVIDENCE_TO_MACHINE_STATUS`
  applied to that node's ``evidence_strength`` — sourced from the schema (the one
  §12.2 authority), never from the compiler, so a compiler that drifted its status
  projection is caught, not blessed.

Two consistency checks strengthen the audit without changing its subject:

* **section membership** — a traced node must declare the same ``section_slug`` as
  the file the claim appears in (a claim traced to a node in the wrong section is a
  finding);
* **no dropped node** — every bound ``proposal_section`` node for a section's slug
  must appear as a ``claim_id`` in that published section, so the ledger is
  complete, not merely a subset.

Findings vs. fail-closed
------------------------
The tool distinguishes *audit findings* (the published Tier-5 disagrees with the
vault — reported, so one run surfaces every problem) from *fail-closed*
preconditions (the audit cannot be run at all — a malformed config/vault, an
unparseable section file, or **no published sections to verify**, which is refused
rather than vacuously passed, §12.4).  It writes nothing and evaluates no gate: a
pure, deterministic, Claude-free reader (§17.6.2).

Generic by construction
-----------------------
Carries no project nouns; the published-sections directory, the vault, and the
node bindings are all resolved from the per-project ``graph.config.yaml``.  As a
``runner/graph_*.py`` module it is auto-covered by the agnosticism lint
(:mod:`runner.agnosticism_lint`, D15) — a second instance audits with only its
config changed.

Constitutional authority:
    Subordinate to CLAUDE.md.  A downstream, read-only verification (§12.1) of
    Tier-5 deliverables against their Tier-5 graph source; it invents no facts
    (§13.3) and prefers an honest failure over a fabricated pass (§12.4/§13.8).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from runner.graph_config import GraphConfig, GraphConfigError, load_graph_config
from runner.graph_schema import EVIDENCE_TO_MACHINE_STATUS
from runner.vault_reader import GraphNode, Vault, VaultReadError, read_vault

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Filename suffix of a published Part B section artifact (``{slug}_section.json``).
#: The slug (the leading component) matches a ``proposal_section`` node's
#: ``section_slug`` front-matter — the same convention the compiler writes.
SECTION_FILE_SUFFIX: str = "_section.json"

#: The closed vocabulary of :attr:`ClaimFinding.kind`.  Named so a construction
#: site and its test refer to one symbol — a typo cannot silently mint a new kind.
KIND_UNTRACEABLE_CLAIM: str = "untraceable_claim"
KIND_STATUS_MISMATCH: str = "status_mismatch"
KIND_SECTION_MISMATCH: str = "section_mismatch"
KIND_DROPPED_NODE: str = "dropped_node"
KIND_MALFORMED_CLAIM: str = "malformed_claim"
KIND_MISSING_CLAIM_BLOCK: str = "missing_claim_block"


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class GraphClaimVerificationError(Exception):
    """Raised when the claim→node audit **cannot be performed**.

    A precondition failure, distinct from an audit *finding*: no tier5
    sections binding in the config, a missing/empty published-sections directory,
    or a section file that is not readable JSON.  Config-load and vault-read
    failures surface as their own (:class:`~runner.graph_config.GraphConfigError`
    / :class:`~runner.vault_reader.VaultReadError`) types.  Every message names the
    offending element; the auditor never vacuously passes.
    """


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClaimFinding:
    """One way a published section disagrees with the vault.

    ``kind`` is one of the module ``KIND_*`` constants: ``untraceable_claim`` (claim_id names no bound
    ``proposal_section`` node), ``status_mismatch`` (published status ≠ the
    Appendix-B map of the node's ``evidence_strength``), ``section_mismatch`` (the
    traced node declares a different ``section_slug`` than the file the claim is
    in), ``dropped_node`` (a bound node for this section's slug has no claim in the
    published ledger), ``malformed_claim`` (a claim entry missing/mistyped
    ``claim_id``/``status``), or ``missing_claim_block`` (the section carries no
    ``validation_status.claim_statuses`` list at all).
    """

    kind: str
    section_file: str
    """Repo-relative POSIX path of the published section the finding is in."""
    slug: str
    """The section slug derived from the file name."""
    claim_id: str
    """The offending claim/node id, or ``""`` for a section-level finding."""
    detail: str
    """A human-readable description of the disagreement."""


@dataclass(frozen=True)
class ClaimVerificationResult:
    """The outcome of a claim→node re-verification run."""

    config_project_id: str
    sections_dir: str
    """Repo-relative POSIX directory the published sections were read from."""
    sections_checked: tuple[str, ...]
    """Every ``*_section.json`` audited (repo-relative POSIX, sorted by name)."""
    claims_checked: int
    """Total number of well-formed published claims examined."""
    vault_section_node_count: int
    """Number of bound ``proposal_section`` vault nodes (the trace-target set)."""
    findings: tuple[ClaimFinding, ...]
    """Every disagreement found, in ``(section-file, claim, completeness)`` order."""

    @property
    def ok(self) -> bool:
        """True when every published claim traces to its vault node cleanly."""
        return not self.findings


# ---------------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------------


def _as_dir(artifact_path: str) -> str:
    """Reduce a binding ``artifact_path`` to its directory (POSIX).

    A directory target is returned as-is; a ``.json`` file target is reduced to
    its parent (mirroring the compiler's ``_partb_out_dir``) so the per-slug
    ``{slug}_section.json`` files are looked for beside it.
    """
    ap = artifact_path.rstrip("/")
    if ap.endswith(".json"):
        return PurePosixPath(ap).parent.as_posix()
    return ap


def _rel(path: Path, repo_root: Path) -> str:
    """Best-effort repo-relative POSIX path (falls back to the absolute posix)."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _tier5_sections_dir(config: GraphConfig) -> str:
    """Resolve the published Part B sections directory from *config*, fail-closed.

    The directory is the ``artifact_path`` of the config's tier5 extraction
    binding(s).  Raises :class:`GraphClaimVerificationError` if no tier5 binding
    declares an ``artifact_path`` (nothing to verify against) or if two route to
    different directories (ambiguous).
    """
    dirs = {
        _as_dir(b.artifact_path)
        for b in config.bindings
        if b.tier == "tier5" and b.artifact_path is not None
    }
    if not dirs:
        raise GraphClaimVerificationError(
            "config declares no tier5 binding with an artifact_path; there is no "
            "published proposal-sections directory to verify claims against"
        )
    if len(dirs) > 1:
        raise GraphClaimVerificationError(
            f"config routes tier5 sections to multiple directories {sorted(dirs)}; "
            f"a single proposal-sections location is required to verify claims"
        )
    return next(iter(dirs))


def _bound_section_nodes(vault: Vault) -> list[GraphNode]:
    """The ``proposal_section`` nodes a tier5 artifact binding selects.

    Mirrors the compiler's node population exactly (``binding.tier == "tier5"`` with
    an ``artifact_path``) so an unbound ``proposal_section`` node — one no config
    binding routes to the sections artifact — is not treated as a valid trace
    target.  In vault (relative-path) order for determinism.
    """
    out: list[GraphNode] = []
    for node in vault.nodes:
        if node.node_type != "proposal_section":
            continue
        binding = vault.binding_for(node)
        if binding is None or binding.tier != "tier5" or binding.artifact_path is None:
            continue
        out.append(node)
    return out


def _section_slug(node: GraphNode) -> Optional[str]:
    """A node's declared ``section_slug`` (stripped), or ``None`` when absent/blank."""
    slug = node.front_matter.get("section_slug")
    if isinstance(slug, str) and slug.strip():
        return slug.strip()
    return None


def _check_claim(
    claim: Any,
    section_file: str,
    slug: str,
    node_by_id: dict[str, GraphNode],
) -> tuple[Optional[str], list[ClaimFinding]]:
    """Audit one published claim entry against the bound vault nodes.

    Returns ``(claim_id, findings)``.  ``claim_id`` is the stripped id when the
    entry is well-formed enough to have one — the caller adds it to the section's
    published-id set (for the completeness check) and counts it as examined —
    else ``None``.  ``findings`` lists every disagreement the claim raises:
    malformation, traceability (``claim_id`` names no bound node), status drift
    (published status ≠ the Appendix-B map of the node's ``evidence_strength``),
    and section membership (the traced node belongs to a different slug).
    """
    if not isinstance(claim, dict):
        return None, [
            ClaimFinding(
                kind=KIND_MALFORMED_CLAIM,
                section_file=section_file,
                slug=slug,
                claim_id="",
                detail=f"a claim_statuses entry is not an object (got {type(claim).__name__})",
            )
        ]

    claim_id = claim.get("claim_id")
    if not isinstance(claim_id, str) or not claim_id.strip():
        return None, [
            ClaimFinding(
                kind=KIND_MALFORMED_CLAIM,
                section_file=section_file,
                slug=slug,
                claim_id="",
                detail=f"a claim is missing a non-empty 'claim_id' (got {claim_id!r})",
            )
        ]
    claim_id = claim_id.strip()

    node = node_by_id.get(claim_id)
    if node is None:
        return claim_id, [
            ClaimFinding(
                kind=KIND_UNTRACEABLE_CLAIM,
                section_file=section_file,
                slug=slug,
                claim_id=claim_id,
                detail="claim_id matches no bound proposal_section vault node id",
            )
        ]

    findings: list[ClaimFinding] = []

    # status fidelity — published status must be the Appendix-B map of the node's
    # evidence_strength (schema-sourced, never compiler-sourced).
    status = claim.get("status")
    if not isinstance(status, str) or not status.strip():
        findings.append(
            ClaimFinding(
                kind=KIND_MALFORMED_CLAIM,
                section_file=section_file,
                slug=slug,
                claim_id=claim_id,
                detail=f"claim is missing a non-empty 'status' (got {status!r})",
            )
        )
    else:
        expected = EVIDENCE_TO_MACHINE_STATUS[node.evidence_strength]
        if status.strip() != expected:
            findings.append(
                ClaimFinding(
                    kind=KIND_STATUS_MISMATCH,
                    section_file=section_file,
                    slug=slug,
                    claim_id=claim_id,
                    detail=(
                        f"published status {status.strip()!r} != Appendix-B map of "
                        f"node evidence_strength {node.evidence_strength!r} "
                        f"(expected {expected!r})"
                    ),
                )
            )

    # section membership — the traced node must belong to this file's slug.
    node_slug = _section_slug(node)
    if node_slug is not None and node_slug != slug:
        findings.append(
            ClaimFinding(
                kind=KIND_SECTION_MISMATCH,
                section_file=section_file,
                slug=slug,
                claim_id=claim_id,
                detail=(
                    f"claim appears in {slug}{SECTION_FILE_SUFFIX} but its node "
                    f"declares section_slug {node_slug!r}"
                ),
            )
        )

    return claim_id, findings


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def verify_claim_traceability(
    config_path: Path, repo_root: Path
) -> ClaimVerificationResult:
    """Independently verify that published Part B claims trace to vault nodes.

    Reads ``config_path`` and its vault (the shared reader, **not** the compiler),
    resolves the published-sections directory from the config, and audits every
    committed ``*_section.json`` against the bound ``proposal_section`` nodes.  It
    re-runs no compile; it audits the artifacts on disk.

    Parameters
    ----------
    config_path:
        The ``graph.config.yaml`` whose vault and tier5 sections directory to audit.
    repo_root:
        Repository root; the published-sections directory is resolved beneath it.

    Returns
    -------
    ClaimVerificationResult
        ``result.ok`` is True iff every published claim traces cleanly.

    Raises
    ------
    GraphConfigError, VaultReadError, GraphClaimVerificationError
        On a malformed config/vault, a config with no tier5 sections binding, a
        missing/empty published-sections directory, or a section file that is not
        readable JSON — the audit's preconditions.  Fails closed, naming the
        offending element; never returns a vacuous pass.
    """
    config = load_graph_config(config_path)
    vault = read_vault(config.resolve_vault_dir(), config)

    sections_dir_rel = _tier5_sections_dir(config)
    sections_dir = repo_root / sections_dir_rel
    if not sections_dir.is_dir():
        raise GraphClaimVerificationError(
            f"published proposal-sections directory not found: {sections_dir_rel} "
            f"(resolved under {repo_root}); there is nothing to verify"
        )
    section_files = sorted(
        (p for p in sections_dir.glob(f"*{SECTION_FILE_SUFFIX}") if p.is_file()),
        key=lambda p: p.name,
    )
    if not section_files:
        raise GraphClaimVerificationError(
            f"no *{SECTION_FILE_SUFFIX} files in {sections_dir_rel}; there are no "
            f"published Part B sections to verify (refusing to vacuously pass)"
        )

    section_nodes = _bound_section_nodes(vault)
    node_by_id: dict[str, GraphNode] = {n.node_id: n for n in section_nodes}
    ids_by_slug: dict[str, set[str]] = {}
    for node in section_nodes:
        slug = _section_slug(node)
        if slug is not None:
            ids_by_slug.setdefault(slug, set()).add(node.node_id)

    findings: list[ClaimFinding] = []
    claims_checked = 0
    sections_checked: list[str] = []

    for path in section_files:
        rel = _rel(path, repo_root)
        sections_checked.append(rel)
        slug = path.name[: -len(SECTION_FILE_SUFFIX)]

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GraphClaimVerificationError(
                f"{rel}: published section is not readable JSON ({exc}); the audit "
                f"cannot verify its claims"
            ) from exc
        if not isinstance(data, dict):
            raise GraphClaimVerificationError(
                f"{rel}: published section is not a JSON object "
                f"(got {type(data).__name__}); the audit cannot verify it"
            )

        vstatus = data.get("validation_status")
        claim_list = (
            vstatus.get("claim_statuses") if isinstance(vstatus, dict) else None
        )
        if not isinstance(claim_list, list):
            findings.append(
                ClaimFinding(
                    kind=KIND_MISSING_CLAIM_BLOCK,
                    section_file=rel,
                    slug=slug,
                    claim_id="",
                    detail=(
                        "validation_status.claim_statuses is absent or not a list; "
                        "the published section carries no claim ledger to trace"
                    ),
                )
            )
            continue

        published_ids: set[str] = set()
        for claim in claim_list:
            claim_id, claim_findings = _check_claim(claim, rel, slug, node_by_id)
            findings.extend(claim_findings)
            if claim_id is not None:
                claims_checked += 1
                published_ids.add(claim_id)

        # completeness — a bound node for this slug missing from the ledger is a
        # dropped claim, not merely an unaudited one (the '⊆' becomes '=').
        for missing in sorted(ids_by_slug.get(slug, set()) - published_ids):
            findings.append(
                ClaimFinding(
                    kind=KIND_DROPPED_NODE,
                    section_file=rel,
                    slug=slug,
                    claim_id=missing,
                    detail=(
                        "a bound proposal_section vault node for this section has no "
                        "corresponding claim_id in the published section (dropped "
                        "from the ledger)"
                    ),
                )
            )

    return ClaimVerificationResult(
        config_project_id=config.project_id,
        sections_dir=sections_dir_rel,
        sections_checked=tuple(sections_checked),
        claims_checked=claims_checked,
        vault_section_node_count=len(section_nodes),
        findings=tuple(findings),
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def format_report(result: ClaimVerificationResult) -> str:
    """Render a human-readable summary of a :class:`ClaimVerificationResult`."""
    header = (
        f"[claim-verify] project={result.config_project_id} "
        f"sections={len(result.sections_checked)} "
        f"claims={result.claims_checked} "
        f"vault_section_nodes={result.vault_section_node_count} "
        f"findings={len(result.findings)}"
    )
    if result.ok:
        return (
            header + "\n"
            "[claim-verify] OK — every published Part B claim traces to a bound "
            "proposal_section vault node with a matching Appendix-B status."
        )
    lines = [header, "[claim-verify] FINDINGS:"]
    for finding in result.findings:
        cid = f" claim={finding.claim_id!r}" if finding.claim_id else ""
        lines.append(
            f"  [{finding.kind}] {finding.section_file}{cid}: {finding.detail}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI  (python -m runner.graph_claim_verifier --config <path>)
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """Run the claim→node re-verification from the command line.

    Exit codes: ``0`` every claim traces cleanly; ``1`` one or more audit findings
    (the published Tier-5 disagrees with the vault; report printed to stderr);
    ``2`` a fail-closed precondition error (bad config/vault, no tier5 sections
    binding, missing/empty sections dir, unparseable section — naming the offending
    element); ``3`` an unexpected error.
    """
    parser = argparse.ArgumentParser(
        prog="python -m runner.graph_claim_verifier",
        description=(
            "Independently verify that every published Part B claim traces to its "
            "proposal_section vault node (DOD-1b) — an auditor that reads the "
            "committed sections, never re-running the compiler."
        ),
    )
    parser.add_argument("--config", required=True, help="Path to graph.config.yaml.")
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root (default: auto-discovered via find_repo_root).",
    )
    args = parser.parse_args(argv)

    from runner.paths import find_repo_root

    try:
        repo_root = (
            Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
        )
        result = verify_claim_traceability(Path(args.config), repo_root)
    except (GraphConfigError, VaultReadError, GraphClaimVerificationError) as exc:
        print(f"[claim-verify] FAIL-CLOSED: {exc}", file=sys.stderr, flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"[claim-verify] ERROR: {exc}", file=sys.stderr, flush=True)
        return 3

    report = format_report(result)
    if result.ok:
        print(report, flush=True)
        return 0
    print(report, file=sys.stderr, flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
