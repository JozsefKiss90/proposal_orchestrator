"""
Node resolver for the runtime integration layer.

Maps ``node_id`` to agent identifiers, skill lists, phase IDs, and file
paths for agent definitions and prompt specifications.  This is a
**read-only resolution layer** that loads the manifest node_registry and
queries the file system.  It contains no business logic, does not execute
agents or skills, and does not evaluate gates.

Authoritative source:
    runtime_integration_plan.md §5 (node_id → agent_id Resolution)
    runtime_integration_plan.md §6 (Agent Prompt / Body Execution Model)
    runtime_integration_execution_plan.md Step 3

Constitutional authority:
    Subordinate to CLAUDE.md.  The manifest node_registry is the sole
    authoritative source for node → agent binding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from runner.manifest_reader import MANIFEST_REL_PATH


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class NodeResolverError(Exception):
    """Raised for missing node_ids or missing agent files."""


# ---------------------------------------------------------------------------
# NodeResolver
# ---------------------------------------------------------------------------


class NodeResolver:
    """Resolves ``node_id`` to agent identifiers, skill lists, and file paths.

    Loaded from ``manifest.compile.yaml``.  All resolution methods return
    data read from the manifest or file system — none execute side effects.

    Parameters
    ----------
    manifest_path:
        Explicit path to the compiled manifest YAML file.  When ``None``,
        resolves to ``repo_root / MANIFEST_REL_PATH``.
    repo_root:
        Repository root directory.  Used for manifest path resolution (when
        *manifest_path* is ``None``) and for agent file path construction.
    """

    def __init__(
        self,
        manifest_path: Optional[Path] = None,
        repo_root: Optional[Path] = None,
    ) -> None:
        if repo_root is None:
            from runner.paths import find_repo_root

            repo_root = find_repo_root()
        self._repo_root: Path = repo_root

        if manifest_path is None:
            manifest_path = repo_root / MANIFEST_REL_PATH

        if not manifest_path.exists():
            raise NodeResolverError(
                f"Compiled manifest not found: {manifest_path}"
            )

        try:
            raw_text = manifest_path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise NodeResolverError(
                f"Cannot read manifest {manifest_path}: {exc}"
            ) from exc

        try:
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            raise NodeResolverError(
                f"Invalid YAML in manifest {manifest_path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise NodeResolverError(
                f"Manifest root is not a dict: {type(data).__name__}"
            )

        node_registry = data.get("node_registry")
        if not isinstance(node_registry, list):
            raise NodeResolverError(
                "Manifest missing or invalid 'node_registry' key"
            )

        # Build O(1) index keyed by node_id, preserving manifest order.
        self._node_index: dict[str, dict] = {}
        self._node_order: list[str] = []
        for entry in node_registry:
            if isinstance(entry, dict) and "node_id" in entry:
                nid = entry["node_id"]
                self._node_index[nid] = entry
                self._node_order.append(nid)

    # ------------------------------------------------------------------
    # Internal lookup
    # ------------------------------------------------------------------

    def _get_entry(self, node_id: str) -> dict:
        """Return the node registry entry for *node_id* or raise."""
        try:
            return self._node_index[node_id]
        except KeyError:
            raise NodeResolverError(
                f"node_id {node_id!r} not found in manifest node_registry. "
                f"Known node_ids: {self._node_order}"
            ) from None

    # ------------------------------------------------------------------
    # Resolution methods
    # ------------------------------------------------------------------

    def node_ids(self) -> list[str]:
        """Return all node_ids in manifest registry order."""
        return list(self._node_order)

    def resolve_agent_id(self, node_id: str) -> str:
        """Return the ``agent`` field for *node_id*.

        Raises :class:`NodeResolverError` if node_id is not found or the
        entry has no ``agent`` field.
        """
        entry = self._get_entry(node_id)
        agent_id = entry.get("agent")
        if agent_id is None:
            raise NodeResolverError(
                f"Node {node_id!r} has no 'agent' field in manifest"
            )
        return agent_id

    def resolve_sub_agent_id(self, node_id: str) -> str | None:
        """Return the ``sub_agent`` field for *node_id*, or ``None``."""
        return self._get_entry(node_id).get("sub_agent")

    def resolve_pre_gate_agent_id(self, node_id: str) -> str | None:
        """Return the ``pre_gate_agent`` field for *node_id*, or ``None``."""
        return self._get_entry(node_id).get("pre_gate_agent")

    def resolve_skill_ids(self, node_id: str) -> list[str]:
        """Return the ``skills`` list for *node_id* in manifest order.

        Returns an empty list if the node has no ``skills`` field.
        """
        entry = self._get_entry(node_id)
        skills = entry.get("skills")
        if skills is None:
            return []
        if not isinstance(skills, list):
            raise NodeResolverError(
                f"Node {node_id!r} 'skills' field is not a list: "
                f"{type(skills).__name__}"
            )
        return list(skills)

    def resolve_phase_id(self, node_id: str) -> str:
        """Return the ``phase_id`` field for *node_id*.

        Raises :class:`NodeResolverError` if node_id is not found or the
        entry has no ``phase_id`` field.
        """
        entry = self._get_entry(node_id)
        phase_id = entry.get("phase_id")
        if phase_id is None:
            raise NodeResolverError(
                f"Node {node_id!r} has no 'phase_id' field in manifest"
            )
        return phase_id

    def agent_definition_path(self, agent_id: str) -> Path:
        """Return the path to ``.claude/agents/<agent_id>.md``.

        Raises :class:`NodeResolverError` if the file does not exist.
        """
        path = self._repo_root / ".claude" / "agents" / f"{agent_id}.md"
        if not path.exists():
            raise NodeResolverError(
                f"Agent definition file not found: {path}"
            )
        return path

    def agent_prompt_spec_path(self, agent_id: str) -> Path:
        """Return the path to ``.claude/agents/prompts/<agent_id>_prompt_spec.md``.

        Raises :class:`NodeResolverError` if the file does not exist.
        """
        path = (
            self._repo_root
            / ".claude"
            / "agents"
            / "prompts"
            / f"{agent_id}_prompt_spec.md"
        )
        if not path.exists():
            raise NodeResolverError(
                f"Agent prompt spec file not found: {path}"
            )
        return path
