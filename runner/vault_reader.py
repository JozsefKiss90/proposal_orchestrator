"""
Deterministic vault reader — the pure-Python parse layer of the graph substrate.

Given a vault directory (and, optionally, a :class:`~runner.graph_config.GraphConfig`),
:func:`read_vault` parses every graph node deterministically — YAML front-matter,
body prose, and wikilinks (Obsidian basename resolution) — validates each against
the generic superset schema (:mod:`runner.graph_schema`), and returns an
indexed :class:`Vault`.  It is the substrate on which the graph→docs compiler
(ticket 3/6), the docs→graph projector (ticket 4), and pack-from-graph (ticket 7)
are mechanical to build.

Guarantees (ticket 1):

* **Pure and deterministic.**  No Claude, no domain reasoning, no timestamps,
  no I/O beyond reading the vault.  The same vault always yields the same parse
  (nodes are ordered by relative path; wikilinks are de-duplicated in first-seen
  order).
* **Fail closed, never silent.**  A ``.md`` node with missing/malformed
  front-matter, an unparseable YAML block, a duplicate ``id`` or basename, or a
  schema violation raises :class:`VaultReadError` **naming the node** — never a
  crash and never a silent skip.  Dangling wikilinks are *recorded*, not fatal
  (a missing target is a graph-quality signal the compiler decides on, not a
  parse error).
* **Basename wikilink resolution.**  ``[[Target]]``, ``[[Target|Display]]``,
  ``[[folder/Target#Heading]]`` all resolve to the node whose file basename (or
  declared ``alias``) is ``Target`` — matching Obsidian's link semantics.

Constitutional authority:
    Subordinate to CLAUDE.md.  This reader extracts nothing to ``docs/**`` and
    makes no gate/DAG change; it only parses.  Provenance is carried faithfully
    via ``evidence_strength`` → status (Appendix B), never inferred.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Optional

import yaml

from runner.graph_config import Binding, GraphConfig
from runner.graph_schema import (
    GraphSchemaError,
    map_evidence_to_status,
    validate_front_matter,
)

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class VaultReadError(Exception):
    """Raised when a vault cannot be read as a well-formed graph.

    Covers: a missing vault directory, a node with no leading front-matter
    block, an unclosed or unparseable front-matter block, front-matter that is
    not a mapping, a schema violation, or a duplicate node ``id``/basename.
    Every message names the offending node.
    """


# ---------------------------------------------------------------------------
# Wikilink parsing
# ---------------------------------------------------------------------------

#: Matches ``[[...]]`` wikilinks.  The inner text may carry a ``folder/`` prefix,
#: a ``#heading`` anchor, and/or a ``|display`` alias — all handled in
#: :func:`_parse_wikilink`.
_WIKILINK_RE = re.compile(r"\[\[([^\[\]]+?)\]\]")


@dataclass(frozen=True)
class WikiLink:
    """A single outgoing wikilink parsed from a node body."""

    target_basename: str
    """The resolved link target basename (folder prefix and ``#heading`` stripped)."""

    display: str
    """The display text (the ``|`` alias if given, else the raw target)."""


def _parse_wikilink(inner: str) -> Optional[WikiLink]:
    """Parse the inner text of a ``[[...]]`` into a :class:`WikiLink`.

    Returns ``None`` for a blank/degenerate link (e.g. ``[[|x]]`` with no target,
    or a pure ``#heading`` self-anchor).
    """
    target_part, _, display_part = inner.partition("|")
    display = display_part.strip() if display_part else ""
    # strip a #heading / #^block anchor
    target_no_anchor = target_part.split("#", 1)[0]
    # Obsidian resolves by basename: keep the last path component only.
    basename = PurePosixPath(target_no_anchor.replace("\\", "/").strip()).name
    basename = basename.strip()
    if not basename:
        return None
    return WikiLink(
        target_basename=basename,
        display=display or target_part.strip(),
    )


def _extract_wikilinks(body: str) -> tuple[WikiLink, ...]:
    """Extract distinct wikilinks from *body*, de-duplicated in first-seen order."""
    seen: dict[str, WikiLink] = {}
    for match in _WIKILINK_RE.finditer(body):
        link = _parse_wikilink(match.group(1))
        if link is None:
            continue
        # de-dupe on (target, display) so ``[[X]]`` and ``[[X|Y]]`` both survive
        key = f"{link.target_basename}\x00{link.display}"
        if key not in seen:
            seen[key] = link
    return tuple(seen.values())


# ---------------------------------------------------------------------------
# Front-matter splitting
# ---------------------------------------------------------------------------


def _split_front_matter(text: str, node_ref: str) -> tuple[str, str]:
    """Split *text* into ``(front_matter_yaml, body)`` using the leading block only.

    The front-matter is the content between the opening ``---`` line and the next
    line that is exactly ``---``.  ``node_type:`` (or any key) appearing later in
    a body code fence is **not** front-matter and is ignored.

    Raises :class:`VaultReadError` (naming *node_ref*) when there is no leading
    ``---`` line or the block is never closed.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise VaultReadError(
            f"{node_ref}: no leading YAML front-matter block "
            f"(file must start with a '---' line)"
        )
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[1:i]), "".join(lines[i + 1 :])
    raise VaultReadError(
        f"{node_ref}: front-matter block is never closed (missing closing '---')"
    )


# ---------------------------------------------------------------------------
# GraphNode
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphNode:
    """A single parsed, schema-valid graph node."""

    node_id: str
    title: str
    node_type: str
    evidence_strength: str
    status: str
    """Validation status from the Appendix-B pure lookup (``Confirmed`` /
    ``Inferred`` / ``Unresolved``)."""

    rel_path: str
    """Path relative to the vault root (POSIX separators)."""
    folder: str
    """The node's folder relative to the vault root ("" at the root)."""
    basename: str
    """The file stem (no ``.md``) — the wikilink resolution key."""

    front_matter: dict[str, Any]
    body: str
    wikilinks: tuple[WikiLink, ...]
    aliases: tuple[str, ...]
    path: Path
    """Absolute path on disk."""

    # ── additive-optional binding fields (None when the node omits them) ──
    @property
    def tier(self) -> Optional[str]:
        return self.front_matter.get("tier")

    @property
    def phase(self) -> Any:
        return self.front_matter.get("phase")

    @property
    def artifact_path(self) -> Optional[str]:
        return self.front_matter.get("artifact_path")

    @property
    def sub_section_id(self) -> Optional[str]:
        return self.front_matter.get("sub_section_id")


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Vault:
    """An indexed, deterministic view over a parsed vault."""

    root: Path
    nodes: tuple[GraphNode, ...]
    by_id: dict[str, GraphNode]
    by_basename: dict[str, GraphNode]
    config: Optional[GraphConfig] = None
    _by_alias: dict[str, GraphNode] = field(default_factory=dict)

    def resolve_link(self, basename: str) -> Optional[GraphNode]:
        """Resolve a wikilink target to a node by basename, then by alias.

        Basename match wins over an alias match; returns ``None`` for a dangling
        link (no such node), which is a recorded graph-quality signal, not an
        error.
        """
        node = self.by_basename.get(basename)
        if node is not None:
            return node
        return self._by_alias.get(basename)

    def binding_for(self, node: GraphNode) -> Optional[Binding]:
        """The :class:`~runner.graph_config.Binding` selecting *node*, or ``None``.

        Returns ``None`` when no config was supplied or no binding matches.
        """
        if self.config is None:
            return None
        return self.config.resolve(node.folder, node.node_type)

    def dangling_links(self) -> tuple[tuple[GraphNode, WikiLink], ...]:
        """All ``(node, wikilink)`` pairs whose target does not resolve.

        Deterministic (node order, then first-seen link order).  Recorded for the
        compiler to decide on; the reader itself never fails on a dangling link.
        """
        out: list[tuple[GraphNode, WikiLink]] = []
        for node in self.nodes:
            for link in node.wikilinks:
                if self.resolve_link(link.target_basename) is None:
                    out.append((node, link))
        return tuple(out)


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------


def _parse_node(path: Path, root: Path) -> GraphNode:
    """Parse a single ``.md`` file into a validated :class:`GraphNode`."""
    rel_path = PurePosixPath(path.relative_to(root).as_posix())
    node_ref = rel_path.as_posix()

    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise VaultReadError(f"{node_ref}: cannot read file: {exc}") from exc

    fm_yaml, body = _split_front_matter(text, node_ref)

    try:
        front_matter = yaml.safe_load(fm_yaml)
    except yaml.YAMLError as exc:
        raise VaultReadError(
            f"{node_ref}: front-matter is not valid YAML: {exc}"
        ) from exc

    # schema validation — translate the schema failure into the reader's single
    # fail-closed type at the module boundary (the node_ref is preserved in the
    # message; the GraphSchemaError remains the __cause__).
    try:
        validate_front_matter(front_matter, node_ref)
    except GraphSchemaError as exc:
        raise VaultReadError(str(exc)) from exc

    evidence_strength = front_matter["evidence_strength"]
    aliases_raw = front_matter.get("aliases") or []
    aliases = tuple(
        str(a).strip() for a in aliases_raw if isinstance(a, (str, int)) and str(a).strip()
    ) if isinstance(aliases_raw, list) else ()

    parent = rel_path.parent.as_posix()
    folder = "" if parent == "." else parent

    return GraphNode(
        node_id=str(front_matter["id"]).strip(),
        title=str(front_matter["title"]).strip(),
        node_type=front_matter["node_type"],
        evidence_strength=evidence_strength,
        status=map_evidence_to_status(evidence_strength),
        rel_path=node_ref,
        folder=folder,
        basename=path.stem,
        front_matter=front_matter,
        body=body,
        wikilinks=_extract_wikilinks(body),
        aliases=aliases,
        path=path,
    )


def read_vault(
    vault_dir: Path,
    config: Optional[GraphConfig] = None,
) -> Vault:
    """Parse a vault deterministically into an indexed :class:`Vault`.

    Parameters
    ----------
    vault_dir:
        The node root to read.  Every ``.md`` file beneath it (excluding
        dot-directories such as ``.obsidian``/``.trash``) must be a well-formed
        node.
    config:
        An optional parsed :class:`~runner.graph_config.GraphConfig` whose
        bindings become queryable via :meth:`Vault.binding_for`.

    Returns
    -------
    Vault
        Nodes ordered by relative path; indexed by ``id``, basename, and alias.

    Raises
    ------
    VaultReadError
        On a missing vault directory or any malformed/duplicate node.  Fails
        closed — it never silently skips a node.
    """
    root = Path(vault_dir)
    if not root.is_dir():
        raise VaultReadError(f"Vault directory not found: {root}")

    # Deterministic cross-OS order: sort by the POSIX relative path string, not by
    # Path objects (Path ordering is case-insensitive on Windows, case-sensitive on
    # POSIX). Skip dot-directories (tooling, not graph content).
    md_files = sorted(
        (
            p
            for p in root.rglob("*.md")
            if p.is_file()
            and not any(
                part.startswith(".") for part in p.relative_to(root).parts[:-1]
            )
        ),
        key=lambda p: p.relative_to(root).as_posix(),
    )

    nodes: list[GraphNode] = []
    by_id: dict[str, GraphNode] = {}
    by_basename: dict[str, GraphNode] = {}
    by_alias: dict[str, GraphNode] = {}

    for path in md_files:
        node = _parse_node(path, root)

        if node.node_id in by_id:
            raise VaultReadError(
                f"Duplicate node id {node.node_id!r}: "
                f"{by_id[node.node_id].rel_path} and {node.rel_path} "
                f"(ids must be unique — they are the registry key)"
            )
        if node.basename in by_basename:
            raise VaultReadError(
                f"Duplicate node basename {node.basename!r}: "
                f"{by_basename[node.basename].rel_path} and {node.rel_path} "
                f"(basenames must be unique — wikilinks resolve by basename)"
            )

        by_id[node.node_id] = node
        by_basename[node.basename] = node
        nodes.append(node)

    # Alias index (basename wins; alias collisions resolve to first-seen in node
    # order — deterministic, and never shadow a real basename).
    for node in nodes:
        for alias in node.aliases:
            if alias not in by_basename and alias not in by_alias:
                by_alias[alias] = node

    return Vault(
        root=root,
        nodes=tuple(nodes),
        by_id=by_id,
        by_basename=by_basename,
        config=config,
        _by_alias=by_alias,
    )
