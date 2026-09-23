"""
``graph.config.yaml`` binding contract — the per-project instantiation layer.

This is the second half of the milestone-2 graph substrate (ticket 1).  The
**schema** (:mod:`runner.graph_schema`) and the **reader**
(:mod:`runner.vault_reader`) carry no project-specific bindings; this contract is
where a per-project vault declares them — which folders and ``node_type``\\ s map
to which target tier and canonical ``docs/**`` ``artifact_path``.

That split is the whole agnosticism story (D15): one generic layer, one
per-project ``graph.config.yaml``.  The generic layer here validates the *shape*
of a config; the concrete bindings live in each project's file.

Config shape
------------

.. code-block:: yaml

    project_id: any-opaque-instance-id      # required, not interpreted as content
    vault_path: methodology_graph           # optional; node root relative to this file
    bindings:
      - match: { node_type: proposal_section }
        tier: tier5
        artifact_path: docs/tier5_deliverables/proposal_sections
      - match: { folder: "04_methodological_routes" }
        tier: tier3                          # source-only (no artifact_path)

A binding matches a node when **every** key present in ``match`` matches the
node (``folder`` by path prefix, ``node_type`` exactly).  Bindings are scanned
in file order and the **first** match wins, so place specific bindings before
general ones.  ``artifact_path`` is optional: a binding with none is *source-only*
(the compiler reads such nodes but writes no canonical artifact for them).

This module performs **no domain reasoning** and **fails closed**
(:class:`GraphConfigError`, naming the offending binding) on any malformed or
missing field — never a silent default.

Constitutional authority:
    Subordinate to CLAUDE.md.  A config binds nodes to the canonical tier paths
    the runner and gates already consume; it does not redefine tiers or gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from runner.graph_schema import NODE_TYPES, TIERS

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class GraphConfigError(Exception):
    """Raised when a ``graph.config.yaml`` is missing, malformed, or invalid.

    Covers: unreadable/empty file, non-mapping root, missing/blank
    ``project_id``, empty ``bindings``, a binding with no ``match`` selector, an
    unknown ``tier`` or ``node_type``, or a malformed field.  Every message names
    the offending binding so the failure is actionable.
    """


# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Binding:
    """One folder/``node_type`` → tier/``artifact_path`` binding."""

    tier: str
    """Target tier (one of :data:`runner.graph_schema.TIERS`)."""

    match_folder: Optional[str] = None
    """Folder selector, matched by path prefix relative to the vault root
    (POSIX separators).  ``None`` means "any folder"."""

    match_node_type: Optional[str] = None
    """``node_type`` selector, matched exactly.  ``None`` means "any type"."""

    artifact_path: Optional[str] = None
    """Canonical ``docs/**`` target this binding extracts to.  ``None`` marks a
    *source-only* binding (read, never written)."""

    collection_key: Optional[str] = None
    """Top-level JSON key under which extracted records are collected in the
    ``artifact_path`` file (e.g. ``objectives``, ``work_packages``).  Optional and
    additive: the compiler (ticket 3) falls back to the ``artifact_path`` filename
    stem when it is absent.  Carried here — not derived — because the canonical key
    is not always the filename stem (``workpackage_seed.json`` → ``work_packages``),
    and deriving it would bake a project-specific naming rule into the generic
    layer.  Ignored for source-only bindings."""

    def matches(self, folder: str, node_type: str) -> bool:
        """True if a node in *folder* with *node_type* is selected by this binding.

        Every selector present must match; an absent selector is a wildcard.
        ``folder`` matches by prefix so a binding on ``"04_routes"`` also selects
        ``"04_routes/sub"``.
        """
        if self.match_node_type is not None and node_type != self.match_node_type:
            return False
        if self.match_folder is not None:
            folder_norm = folder.replace("\\", "/").strip("/")
            target = self.match_folder.replace("\\", "/").strip("/")
            if folder_norm != target and not folder_norm.startswith(target + "/"):
                return False
        return True


# ---------------------------------------------------------------------------
# GraphConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphConfig:
    """A parsed, validated ``graph.config.yaml``."""

    project_id: str
    bindings: tuple[Binding, ...]
    source_path: Path
    """Absolute path of the config file this was loaded from."""

    vault_path: Optional[str] = None
    """Node root relative to :attr:`source_path`'s directory, if declared."""

    def resolve_vault_dir(self) -> Path:
        """Absolute vault directory: ``vault_path`` resolved against the config
        file's directory, or that directory itself when ``vault_path`` is unset."""
        base = self.source_path.parent
        return (base / self.vault_path) if self.vault_path else base

    def resolve(self, folder: str, node_type: str) -> Optional[Binding]:
        """Return the first :class:`Binding` selecting a node, or ``None``.

        Scans :attr:`bindings` in file order; first match wins.
        """
        for binding in self.bindings:
            if binding.matches(folder, node_type):
                return binding
        return None


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GraphConfigError(f"{label} is not a mapping (got {type(value).__name__})")
    return value


def _optional_stripped_str(value: Any, label: str) -> Optional[str]:
    """Return a stripped non-empty string, ``None`` when absent, else fail closed.

    The single "non-empty string when present" guard shared by the optional
    ``folder`` / ``artifact_path`` / ``vault_path`` fields.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise GraphConfigError(
            f"{label} must be a non-empty string when present (got {value!r})"
        )
    return value.strip()


def _parse_binding(raw: Any, index: int) -> Binding:
    """Parse and validate one ``bindings[]`` entry, failing closed by index."""
    label = f"bindings[{index}]"
    entry = _require_mapping(raw, label)

    # tier — required, must be a known tier
    tier = entry.get("tier")
    if tier not in TIERS:
        raise GraphConfigError(
            f"{label}: missing or invalid 'tier' {tier!r}; "
            f"expected one of {sorted(TIERS)}"
        )

    # match — required, at least one selector
    match = _require_mapping(entry.get("match"), f"{label}.match")
    match_node_type = match.get("node_type")
    if match.get("folder") is None and match_node_type is None:
        raise GraphConfigError(
            f"{label}.match must specify at least one of 'folder' or 'node_type'"
        )
    match_folder = _optional_stripped_str(match.get("folder"), f"{label}.match.folder")
    if match_node_type is not None and match_node_type not in NODE_TYPES:
        raise GraphConfigError(
            f"{label}.match.node_type {match_node_type!r} is not a known node_type; "
            f"expected one of {sorted(NODE_TYPES)}"
        )

    artifact_path = _optional_stripped_str(
        entry.get("artifact_path"), f"{label}.artifact_path"
    )
    collection_key = _optional_stripped_str(
        entry.get("collection_key"), f"{label}.collection_key"
    )
    if collection_key is not None and artifact_path is None:
        raise GraphConfigError(
            f"{label}: 'collection_key' is set but 'artifact_path' is not; "
            f"collection_key names the JSON key of an extracted artifact and is "
            f"meaningless on a source-only binding — remove one or the other"
        )

    return Binding(
        tier=tier,
        match_folder=match_folder,
        match_node_type=match_node_type,
        artifact_path=artifact_path,
        collection_key=collection_key,
    )


def load_graph_config(config_path: Path) -> GraphConfig:
    """Load and validate a ``graph.config.yaml``, failing closed.

    Parameters
    ----------
    config_path:
        Path to the config file.

    Returns
    -------
    GraphConfig
        The parsed, validated config with :attr:`GraphConfig.source_path` set to
        the resolved absolute path of *config_path*.

    Raises
    ------
    GraphConfigError
        On a missing/empty/unparseable file, a non-mapping root, a missing or
        blank ``project_id``, an empty ``bindings`` list, or any malformed
        binding.  Never returns a partial config.
    """
    path = Path(config_path)
    if not path.is_file():
        raise GraphConfigError(f"graph.config.yaml not found: {path}")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise GraphConfigError(f"Cannot read graph.config.yaml ({path}): {exc}") from exc
    if not text.strip():
        raise GraphConfigError(f"graph.config.yaml is empty: {path}")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise GraphConfigError(
            f"graph.config.yaml is not valid YAML ({path}): {exc}"
        ) from exc

    root = _require_mapping(data, "graph.config.yaml root")

    project_id = root.get("project_id")
    if not isinstance(project_id, str) or not project_id.strip():
        raise GraphConfigError(
            f"graph.config.yaml ({path}): missing or blank 'project_id'"
        )

    vault_path = _optional_stripped_str(
        root.get("vault_path"), f"graph.config.yaml ({path}): 'vault_path'"
    )

    raw_bindings = root.get("bindings")
    if not isinstance(raw_bindings, list) or not raw_bindings:
        raise GraphConfigError(
            f"graph.config.yaml ({path}): 'bindings' must be a non-empty list"
        )

    bindings = tuple(
        _parse_binding(raw, i) for i, raw in enumerate(raw_bindings)
    )

    return GraphConfig(
        project_id=project_id.strip(),
        bindings=bindings,
        source_path=path.resolve(),
        vault_path=vault_path,
    )
