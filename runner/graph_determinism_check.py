"""
Determinism re-check of ``--from-graph`` — the DOD-1c replay auditor
(milestone 2, ticket 8.3).

The graph→docs compiler (:mod:`runner.graph_compiler`) is meant to be a **pure,
deterministic function of the vault**: the same vault, compiled twice, must
produce byte-identical staging — the reproducibility guarantee the whole
milestone-2 graph-as-source design rests on (§9.5).  DOD-1c is the standing proof
of that: *re-run ``--from-graph``, confirm byte-identical staging.*

This module is that re-check.  Unlike the claim→node auditor (:mod:`runner`
``.graph_claim_verifier``, DOD-1b), whose honesty comes from **not** running the
compiler, this tool's honesty comes from running it **twice, independently** — two
fresh vault reads into two separate staging roots — and proving the two outputs
agree byte-for-byte.  Any hidden nondeterminism in the compiler (hash-ordered
iteration, an unsorted set, wall-clock leakage into content) surfaces here as a
divergence: the comparison is byte-exact on the fast path and, when only the
excluded stamp forces the bytes apart, falls back to **order-preserving** canonical
JSON, so a reordered key or array element is flagged, not masked (§9.5).

The one legitimately-floating field
-----------------------------------
Exactly one field differs between two compiles of the same vault: the compiler's
own wall-clock publication stamp ``_provenance.compiled_at`` — a sibling of the
gate evaluator's ``evaluated_at`` and the checkpoint's ``published_at``, carrying
no vault-derived content.  It is the **one documented replay-invariant exclusion**
(:data:`REPLAY_INVARIANT_EXCLUSIONS`) this check normalises out before comparing.
To prove that exclusion is *sufficient* — that ``compiled_at`` is the sole field
that floats — the two compiles are fed **deliberately different** ``compiled_at``
values (:data:`_COMPILE_NOW_A` / :data:`_COMPILE_NOW_B`), so the check demonstrates
the strong claim (*even when the stamp differs maximally, nothing else does*)
rather than the weak one (two runs that happened to share a clock tick).  Every
other input is held identical: the same vault and the same ``run_id`` (a
run-scoped parameter, not a vault fact — the committed Part B sections carry the
real run's id, so a determinism check must hold it fixed across the two runs).

Findings vs. fail-closed
------------------------
The tool distinguishes *findings* (the two compiles diverge beyond the documented
exclusion — a real nondeterminism defect, reported so one run surfaces it) from
*fail-closed* preconditions (the check cannot run at all — a malformed
config/vault, or a config that compiles to **nothing**, which is refused rather
than vacuously passed, §12.4).  It writes only to the two ephemeral staging roots
it compares (never over ``docs/`` — it calls the bare ``compile_*`` functions, not
the ``*_and_report`` wrappers, so no repo report is emitted) and evaluates no
gate: a deterministic, Claude-free reader (§17.6.2).

Generic by construction
-----------------------
Carries no project nouns; the vault, the bindings, and the staged artifacts are
all resolved from the per-project ``graph.config.yaml``.  As a
``runner/graph_*.py`` module it is auto-covered by the agnosticism lint
(:mod:`runner.agnosticism_lint`, D15) — a second instance re-checks with only its
config changed.

Constitutional authority:
    Subordinate to CLAUDE.md.  A read-only reproducibility check (§9.5) of the
    compiler against itself; it invents no facts (§13.3) and prefers an honest
    failure over a fabricated pass (§12.4 / §13.8).
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from runner.graph_compiler import (
    GraphCompileError,
    compile_part_b,
    compile_tier3,
)
from runner.graph_config import GraphConfigError, load_graph_config
from runner.vault_reader import VaultReadError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The JSON field path(s) that legitimately **float** across two compiles of the
#: same vault: wall-clock publication stamps that carry no vault-derived content.
#: ``_provenance.compiled_at`` is the compiler's own timestamp (a sibling of the
#: gate evaluator's ``evaluated_at`` and the checkpoint's ``published_at``); it is
#: the SOLE field that differs when one vault is compiled twice, so it is the one
#: documented replay-invariant exclusion the check normalises out before
#: comparing.  Each entry is a tuple of nested object keys (a JSON pointer).  The
#: decision to KEEP ``compiled_at`` as provenance (rather than drop it for literal
#: byte-identity) is recorded in
#: ``decision_log/dod-1c-determinism-recheck-from-graph_2026-07-28.json``.
REPLAY_INVARIANT_EXCLUSIONS: tuple[tuple[str, ...], ...] = (
    ("_provenance", "compiled_at"),
)

#: Two distinct sentinel ``compiled_at`` values fed to the two comparison
#: compiles.  Making them differ **maximally** (rather than sharing a wall clock
#: that might coincide sub-second) is deliberate: it forces the one legitimately-
#: floating field apart so the check proves ``compiled_at`` is the *only* thing
#: that floats.  Any determinism defect surfaces as a divergence beyond these.
_COMPILE_NOW_A: str = "0001-01-01T00:00:00+00:00"
_COMPILE_NOW_B: str = "9999-12-31T23:59:59+00:00"

#: The closed vocabulary of :attr:`DeterminismFinding.kind`.  Named so a
#: construction site and its test refer to one symbol — a typo cannot silently
#: mint a new kind.
KIND_MISSING_FILE: str = "missing_staged_file"
KIND_BYTE_DIVERGENCE: str = "byte_divergence"


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class DeterminismCheckError(Exception):
    """Raised when the determinism re-check **cannot be performed**.

    A precondition failure, distinct from a *finding*: a config that compiles to
    no staged artifacts at all (nothing to compare — refused rather than vacuously
    passed).  Config-load, vault-read, and compile failures surface as their own
    (:class:`~runner.graph_config.GraphConfigError` /
    :class:`~runner.vault_reader.VaultReadError` /
    :class:`~runner.graph_compiler.GraphCompileError`) types.  Every message names
    the offending element; the check never vacuously passes.
    """


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeterminismFinding:
    """One way two compiles of the same vault diverge.

    ``kind`` is one of the module ``KIND_*`` constants: ``missing_staged_file`` (a
    staged artifact present in one compile but not the other — the *set* of files
    is nondeterministic) or ``byte_divergence`` (a staged artifact differs even
    after the documented :data:`REPLAY_INVARIANT_EXCLUSIONS` are normalised out —
    real content nondeterminism).
    """

    kind: str
    staged_file: str
    """The staged artifact's path, relative to its staging root (POSIX)."""
    detail: str
    """A human-readable description of the divergence."""


@dataclass(frozen=True)
class StagingComparison:
    """The byte-level comparison of two populated staging trees."""

    compared_files: tuple[str, ...]
    """Every staged path examined (union of both trees, POSIX, sorted)."""
    byte_identical_files: tuple[str, ...]
    """Paths whose bytes were identical with no normalisation needed."""
    timestamp_normalized_files: tuple[str, ...]
    """Paths that differed only in the documented replay-invariant exclusion(s)
    (i.e. ``compiled_at``) and were equal once those were normalised out."""
    findings: tuple[DeterminismFinding, ...]
    """Every divergence beyond the documented exclusion(s)."""

    @property
    def ok(self) -> bool:
        """True when the two trees agree modulo the documented exclusion(s)."""
        return not self.findings


@dataclass(frozen=True)
class DeterminismResult:
    """The outcome of a ``--from-graph`` determinism re-check."""

    config_project_id: str
    run_id: str
    """The run id held fixed across both compiles (defaults to the project id)."""
    comparison: StagingComparison

    @property
    def ok(self) -> bool:
        """True when the two independent compiles agree modulo ``compiled_at``."""
        return self.comparison.ok

    @property
    def staged_file_count(self) -> int:
        return len(self.comparison.compared_files)


# ---------------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------------


def _strip_exclusions(obj: Any) -> Any:
    """Return a copy of *obj* with each :data:`REPLAY_INVARIANT_EXCLUSIONS` path
    removed (non-mutating).

    Each exclusion is a nested-key path (a JSON pointer).  A path that does not
    resolve (the parent is absent or not an object) is a no-op — the exclusion is
    permissive, never an error, so a staged artifact that simply carries no
    ``_provenance`` block compares on its full content.
    """
    out = copy.deepcopy(obj)
    for path in REPLAY_INVARIANT_EXCLUSIONS:
        node = out
        for key in path[:-1]:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(key)
        if isinstance(node, dict):
            node.pop(path[-1], None)
    return out


def _canonical_json(obj: Any) -> str:
    """Serialise *obj* to a canonical string with the exclusions removed.

    Used to compare two staged JSON artifacts **byte-faithfully modulo the
    documented exclusions**: the serialisation is **order-preserving**
    (``sort_keys=False``) so that a divergence in anything but the excluded
    field(s) — a changed value, a reordered key, a numeric-type change
    (``1`` vs ``1.0``) — produces different bytes and is flagged, not masked by
    dict equality.  Only :func:`_strip_exclusions` (i.e. ``compiled_at``) is
    normalised away.  Internal consistency (both sides serialised identically) is
    all that is required; it need not reproduce the compiler's exact bytes.
    """
    return json.dumps(
        _strip_exclusions(obj), sort_keys=False, ensure_ascii=False, indent=2
    )


def _staged_rel_paths(staging_root: Path) -> dict[str, Path]:
    """Map every file under *staging_root* to its staging-root-relative POSIX path.

    The compiler writes ``docs/**`` JSON beneath the staging root, but this globs
    **all** files (not just ``*.json``) so a non-JSON staged artifact is compared
    too — byte-for-byte — rather than silently skipped (no silent narrowing of the
    comparison surface).  Directories are excluded via ``is_file()``.
    """
    out: dict[str, Path] = {}
    for path in staging_root.rglob("*"):
        if path.is_file():
            out[path.relative_to(staging_root).as_posix()] = path
    return out


def _divergence_detail(rel: str, obj_a: Any, obj_b: Any) -> str:
    """Describe *where* two staged objects differ after normalisation.

    Best-effort: the differing top-level keys, and — when both differ inside a
    shared mapping value — its differing sub-keys, so a real defect names the
    field.  Purely diagnostic; the finding stands regardless of detail quality.
    """
    if isinstance(obj_a, dict) and isinstance(obj_b, dict):
        top = sorted(
            k for k in set(obj_a) | set(obj_b) if obj_a.get(k) != obj_b.get(k)
        )
        parts: list[str] = []
        for key in top:
            va, vb = obj_a.get(key), obj_b.get(key)
            if isinstance(va, dict) and isinstance(vb, dict):
                sub = sorted(
                    s for s in set(va) | set(vb) if va.get(s) != vb.get(s)
                )
                parts.append(f"{key}({', '.join(sub)})" if sub else key)
            else:
                parts.append(key)
        return (
            f"{rel}: two compiles diverge beyond compiled_at at "
            f"{', '.join(parts)} — the compiler is not deterministic for this "
            f"artifact"
        )
    return (
        f"{rel}: two compiles produced different (non-object) content beyond "
        f"compiled_at — the compiler is not deterministic for this artifact"
    )


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------


def compare_staging_trees(root_a: Path, root_b: Path) -> StagingComparison:
    """Byte-compare two populated staging trees modulo the documented exclusions.

    For each staged file under either root (keyed by its staging-root-relative
    path): a file in only one tree is a :data:`KIND_MISSING_FILE` finding; a file
    in both is compared byte-for-byte — identical bytes pass immediately, and
    differing bytes are re-compared as **order-preserving canonical JSON**
    (:func:`_canonical_json`) with :data:`REPLAY_INVARIANT_EXCLUSIONS` normalised
    out (equal → a tolerated ``compiled_at`` float; still unequal, or unparseable →
    a :data:`KIND_BYTE_DIVERGENCE` finding).  Because the canonicalisation
    preserves key order and numeric representation, a divergence in anything but
    ``compiled_at`` — including a reordered key or a numeric-type change — is
    flagged, not masked.  Pure: reads the two trees, writes nothing.
    """
    files_a = _staged_rel_paths(root_a)
    files_b = _staged_rel_paths(root_b)
    all_rels = sorted(set(files_a) | set(files_b))

    byte_identical: list[str] = []
    normalized: list[str] = []
    findings: list[DeterminismFinding] = []

    for rel in all_rels:
        pa = files_a.get(rel)
        pb = files_b.get(rel)
        if pa is None or pb is None:
            present, absent = ("A", "B") if pb is None else ("B", "A")
            findings.append(
                DeterminismFinding(
                    kind=KIND_MISSING_FILE,
                    staged_file=rel,
                    detail=(
                        f"{rel}: staged by compile {present} but not compile "
                        f"{absent}; the set of emitted artifacts is nondeterministic"
                    ),
                )
            )
            continue

        bytes_a = pa.read_bytes()
        bytes_b = pb.read_bytes()
        if bytes_a == bytes_b:
            byte_identical.append(rel)
            continue

        # Bytes differ — the only tolerated cause is the documented exclusion.
        try:
            obj_a = json.loads(bytes_a.decode("utf-8"))
            obj_b = json.loads(bytes_b.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            findings.append(
                DeterminismFinding(
                    kind=KIND_BYTE_DIVERGENCE,
                    staged_file=rel,
                    detail=(
                        f"{rel}: two compiles produced byte-differing, "
                        f"non-JSON content — cannot normalise; nondeterministic"
                    ),
                )
            )
            continue

        if _canonical_json(obj_a) == _canonical_json(obj_b):
            normalized.append(rel)
        else:
            findings.append(
                DeterminismFinding(
                    kind=KIND_BYTE_DIVERGENCE,
                    staged_file=rel,
                    detail=_divergence_detail(rel, obj_a, obj_b),
                )
            )

    return StagingComparison(
        compared_files=tuple(all_rels),
        byte_identical_files=tuple(byte_identical),
        timestamp_normalized_files=tuple(normalized),
        findings=tuple(findings),
    )


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def verify_compile_determinism(
    config_path: Path,
    repo_root: Path,
    staging_root_a: Optional[Path] = None,
    staging_root_b: Optional[Path] = None,
) -> DeterminismResult:
    """Re-check that ``--from-graph`` compiles the vault deterministically.

    Compiles the config's Tier-3 ``architecture_inputs`` and Part B
    ``proposal_section`` artifacts **twice** — two fresh vault reads into two
    separate staging roots, the same ``run_id`` held fixed, and two deliberately
    different ``compiled_at`` stamps — then compares the two staging trees modulo
    the documented :data:`REPLAY_INVARIANT_EXCLUSIONS`.  Non-destructive: it calls
    the bare ``compile_*`` functions (not the ``*_and_report`` wrappers), so it
    writes only to the two staging roots and never over ``docs/``.

    Parameters
    ----------
    config_path:
        The ``graph.config.yaml`` whose vault to compile twice.
    repo_root:
        Repository root (the compiler resolves the vault beneath it).
    staging_root_a, staging_root_b:
        The two staging roots to compile into.  When omitted, two fresh temp
        directories are created and removed afterwards; tests pass explicit dirs
        to inspect the staged bytes.  **Must be distinct** when both are given.

    Returns
    -------
    DeterminismResult
        ``result.ok`` is True iff the two compiles agree modulo ``compiled_at``.

    Raises
    ------
    GraphConfigError, VaultReadError, GraphCompileError
        On a malformed config/vault or an internally inconsistent node/binding —
        the compiler's own fail-closed conditions.
    DeterminismCheckError
        When the config compiles to no staged artifacts at all (nothing to
        re-check — refusing to vacuously pass), or when the two staging roots are
        the same path.  Fails closed, naming the cause.
    """
    if (
        staging_root_a is not None
        and staging_root_b is not None
        and staging_root_a.resolve() == staging_root_b.resolve()
    ):
        raise DeterminismCheckError(
            f"the two staging roots must be distinct paths (got {staging_root_a} "
            f"for both); the second compile would overwrite the first"
        )

    config = load_graph_config(config_path)
    run_id = config.project_id  # held fixed across both compiles (run-scoped)

    tmp_dirs: list[Path] = []
    try:
        root_a = staging_root_a
        root_b = staging_root_b
        if root_a is None:
            root_a = Path(tempfile.mkdtemp(prefix="det-check-a-"))
            tmp_dirs.append(root_a)
        if root_b is None:
            root_b = Path(tempfile.mkdtemp(prefix="det-check-b-"))
            tmp_dirs.append(root_b)

        # Two independent compiles. run_id fixed; compiled_at deliberately apart.
        compile_tier3(config_path, repo_root, staging_root=root_a, now=_COMPILE_NOW_A)
        compile_tier3(config_path, repo_root, staging_root=root_b, now=_COMPILE_NOW_B)
        compile_part_b(
            config_path, repo_root, staging_root=root_a, now=_COMPILE_NOW_A,
            run_id=run_id,
        )
        compile_part_b(
            config_path, repo_root, staging_root=root_b, now=_COMPILE_NOW_B,
            run_id=run_id,
        )

        comparison = compare_staging_trees(root_a, root_b)
    finally:
        for d in tmp_dirs:
            _remove_tree(d)

    if not comparison.compared_files:
        raise DeterminismCheckError(
            f"config {config.project_id!r} compiled to no staged artifacts; there "
            f"is nothing to re-check (refusing to vacuously pass)"
        )

    return DeterminismResult(
        config_project_id=config.project_id,
        run_id=run_id,
        comparison=comparison,
    )


def _remove_tree(path: Path) -> None:
    """Best-effort recursive delete of a temp staging root (never raises)."""
    shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def format_report(result: DeterminismResult) -> str:
    """Render a human-readable summary of a :class:`DeterminismResult`."""
    c = result.comparison
    header = (
        f"[determinism] project={result.config_project_id} "
        f"run_id={result.run_id} "
        f"files={result.staged_file_count} "
        f"byte_identical={len(c.byte_identical_files)} "
        f"compiled_at_normalized={len(c.timestamp_normalized_files)} "
        f"findings={len(c.findings)}"
    )
    if result.ok:
        return (
            header + "\n"
            "[determinism] OK — two independent compiles of the vault are "
            "byte-identical modulo the documented compiled_at stamp."
        )
    lines = [header, "[determinism] FINDINGS:"]
    for finding in c.findings:
        lines.append(f"  [{finding.kind}] {finding.detail}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI  (python -m runner.graph_determinism_check --config <path>)
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """Run the ``--from-graph`` determinism re-check from the command line.

    Exit codes: ``0`` the two compiles agree modulo ``compiled_at``; ``1`` one or
    more findings (the compiler is nondeterministic; report to stderr); ``2`` a
    fail-closed precondition error (bad config/vault, inconsistent binding, or a
    config that compiles to nothing — naming the cause); ``3`` an unexpected error.
    """
    parser = argparse.ArgumentParser(
        prog="python -m runner.graph_determinism_check",
        description=(
            "Re-check that --from-graph compiles the vault deterministically: "
            "compile twice and confirm byte-identical staging modulo the "
            "documented compiled_at stamp (DOD-1c)."
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
        result = verify_compile_determinism(Path(args.config), repo_root)
    except (
        GraphConfigError,
        VaultReadError,
        GraphCompileError,
        DeterminismCheckError,
    ) as exc:
        print(f"[determinism] FAIL-CLOSED: {exc}", file=sys.stderr, flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"[determinism] ERROR: {exc}", file=sys.stderr, flush=True)
        return 3

    report = format_report(result)
    if result.ok:
        print(report, flush=True)
        return 0
    print(report, file=sys.stderr, flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
