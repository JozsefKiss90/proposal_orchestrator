"""
Vault scaffolder — instantiate a fresh per-project graph vault from the generic
template (milestone 2, ticket 5).

The generic template at ``templates/obsidian_graph_vault/`` carries the schema
superset, the ``00…18`` folder skeleton, Dataview (enabled + vendored), and a
generic ``graph.config.yaml`` — with **zero project nouns**.  This module copies
that template to a new location and swaps in the project's ``project_id``,
producing a vault the reader (:mod:`runner.vault_reader`) and compiler
(:mod:`runner.graph_compiler`) accept.  It is the deterministic engine the
``obsidian-graph`` scaffolding skill drives.

It is **pure and Claude-free**: a deterministic copy + a single targeted
``project_id`` rewrite (comments in the template config are preserved).  It
performs no domain reasoning and authors no content — a scaffolded vault is empty
of project facts until a human authors nodes into it.

Constitutional authority:
    Subordinate to CLAUDE.md.  Scaffolding writes only into the target directory;
    it makes no tier, gate, or DAG change.  The whole agnosticism story (D15):
    one generic template here, one per-project ``graph.config.yaml`` per instance.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from runner.graph_config import GraphConfig, load_graph_config
from runner.vault_reader import Vault, read_vault

#: The in-tree home of the generic template (repo-relative).  Documented default;
#: callers may pass any template dir (path-agnostic by design).
DEFAULT_TEMPLATE_REL: str = "templates/obsidian_graph_vault"

_PROJECT_ID_RE = re.compile(r"^(project_id:).*$", re.MULTILINE)


class VaultScaffoldError(Exception):
    """Raised when a vault cannot be scaffolded (bad template, target collision,
    missing ``project_id`` line)."""


@dataclass(frozen=True)
class ScaffoldResult:
    """The outcome of scaffolding a vault."""

    target_dir: Path
    """The Obsidian vault root that was written (holds ``.obsidian`` + config)."""
    config_path: Path
    """The written ``graph.config.yaml``."""
    node_root: Path
    """The node root the reader/compiler read (``target_dir`` + ``vault_path``)."""
    project_id: str


def scaffold_vault(
    template_dir: Path,
    target_dir: Path,
    project_id: str,
    *,
    force: bool = False,
) -> ScaffoldResult:
    """Copy the generic template to *target_dir* and set *project_id*.

    Parameters
    ----------
    template_dir:
        The generic template root (must contain a ``graph.config.yaml``).
    target_dir:
        Where to create the new vault.  Must not already contain files unless
        *force* is set.
    project_id:
        The new instance's opaque id (written into the copied config).
    force:
        Overwrite/merge into a non-empty *target_dir* when set.

    Returns
    -------
    ScaffoldResult

    Raises
    ------
    VaultScaffoldError
        On a missing template config, a non-empty target without *force*, a blank
        ``project_id``, or a template config missing a ``project_id:`` line.
    """
    template_dir = Path(template_dir)
    target_dir = Path(target_dir)

    if not project_id or not project_id.strip():
        raise VaultScaffoldError("project_id must be a non-empty string")
    project_id = project_id.strip()

    template_config = template_dir / "graph.config.yaml"
    if not template_config.is_file():
        raise VaultScaffoldError(
            f"template has no graph.config.yaml: {template_config}"
        )

    if target_dir.exists() and any(target_dir.iterdir()) and not force:
        raise VaultScaffoldError(
            f"target directory is not empty: {target_dir} (pass force=True to merge)"
        )

    shutil.copytree(template_dir, target_dir, dirs_exist_ok=True)

    # Swap in the project_id, preserving the template config's comments.
    config_path = target_dir / "graph.config.yaml"
    text = config_path.read_text(encoding="utf-8")
    new_text, n = _PROJECT_ID_RE.subn(rf"\1 {project_id}", text, count=1)
    if n == 0:
        raise VaultScaffoldError(
            f"template config has no 'project_id:' line to set: {config_path}"
        )
    config_path.write_text(new_text, encoding="utf-8")

    config = load_graph_config(config_path)
    return ScaffoldResult(
        target_dir=target_dir,
        config_path=config_path,
        node_root=config.resolve_vault_dir(),
        project_id=project_id,
    )


def validate_scaffold(result: ScaffoldResult) -> Vault:
    """Confirm a scaffolded vault is one the reader and compiler accept.

    Loads the config, reads the vault, and checks the D6 no-overlap invariant.
    Returns the parsed :class:`~runner.vault_reader.Vault`.  Raises the reader's,
    config's, or projector's own fail-closed exception on any problem.
    """
    from runner.graph_projector import check_no_overlap

    config: GraphConfig = load_graph_config(result.config_path)
    vault = read_vault(result.node_root, config)
    check_no_overlap(config)
    return vault
