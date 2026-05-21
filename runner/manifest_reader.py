"""
Manifest reader for Approach B gate evaluation.

Loads ``manifest.compile.yaml`` and exposes the predicate composition for each
gate via :meth:`ManifestReader.get_predicate_refs`.

In Approach B the manifest is the **composition source**: its gate conditions
each carry a ``predicate_refs`` list that names the predicate IDs to evaluate.
The gate rules library (``gate_rules_library.yaml``) becomes the
**implementation registry**: the runner looks up each predicate ID there to
obtain its full definition (type, function, args).

This is a read-only loader.  It does not validate version coupling — version
checks are the responsibility of :class:`runner.gate_library.GateLibrary`.

See gate_rules_library_plan.md §9 for the Approach B migration specification.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Repo-relative path to the compiled manifest.
MANIFEST_REL_PATH: str = (
    ".claude/workflows/system_orchestration/manifest.compile.yaml"
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ManifestReaderError(Exception):
    """Raised for manifest loading or structural errors."""


class ManifestGateNotFoundError(ManifestReaderError):
    """Raised when a requested ``gate_id`` is not present in the manifest."""


# ---------------------------------------------------------------------------
# ManifestReader
# ---------------------------------------------------------------------------


class ManifestReader:
    """
    In-memory representation of the loaded compiled manifest.

    Instances are created via :meth:`load`.

    The reader indexes the ``gate_registry`` list by ``gate_id`` and provides
    :meth:`get_predicate_refs` to retrieve the ordered list of predicate IDs
    for a gate.  Only conditions whose entries are dicts with a
    ``predicate_refs`` key are considered; plain-string conditions (Approach A
    prose-only format) are silently skipped so that a partially migrated
    manifest does not break loading.
    """

    def __init__(self, data: dict) -> None:
        self._data: dict = data
        # Build an O(1) lookup index keyed by gate_id
        self._gate_index: dict[str, dict] = {
            g["gate_id"]: g
            for g in data.get("gate_registry", [])
            if isinstance(g, dict) and "gate_id" in g
        }

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        manifest_path: Optional[Path] = None,
        *,
        repo_root: Optional[Path] = None,
    ) -> "ManifestReader":
        """
        Load the compiled manifest from disk.

        Parameters
        ----------
        manifest_path:
            Explicit path to the YAML file.  When ``None``, resolves to
            ``repo_root / MANIFEST_REL_PATH``.  If ``repo_root`` is also
            ``None``, auto-discovers the repository root via
            :func:`runner.paths.find_repo_root`.
        repo_root:
            Repository root.  Used only when *manifest_path* is ``None``.

        Raises
        ------
        ManifestReaderError
            File not found, invalid YAML, missing ``gate_registry`` key, or
            ``gate_registry`` is not a list.
        """
        if manifest_path is None:
            if repo_root is None:
                from runner.paths import find_repo_root
                repo_root = find_repo_root()
            manifest_path = repo_root / MANIFEST_REL_PATH

        if not manifest_path.exists():
            raise ManifestReaderError(
                f"Compiled manifest not found: {manifest_path}"
            )

        try:
            raw_text = manifest_path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise ManifestReaderError(
                f"Cannot read manifest {manifest_path}: {exc}"
            ) from exc

        try:
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            raise ManifestReaderError(
                f"Invalid YAML in manifest {manifest_path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ManifestReaderError(
                f"Manifest root must be a YAML mapping; got {type(data).__name__}"
            )

        if "gate_registry" not in data:
            raise ManifestReaderError(
                "Manifest is missing required top-level key 'gate_registry'"
            )

        gate_registry = data["gate_registry"]
        if not isinstance(gate_registry, list):
            raise ManifestReaderError(
                "'gate_registry' must be a YAML sequence (list of gate entries)"
            )

        return cls(data)

    # ------------------------------------------------------------------
    # Predicate composition
    # ------------------------------------------------------------------

    def get_predicate_refs(self, gate_id: str) -> Optional[list[str]]:
        """
        Return the ordered list of predicate IDs for *gate_id*.

        Collects ``predicate_refs`` from every condition object in the gate's
        ``conditions`` list (Approach B format).  Plain-string conditions
        are skipped.

        Returns
        -------
        list[str]
            Flat ordered list of predicate IDs, preserving condition order and
            the order within each condition's ``predicate_refs`` list.
        None
            When the gate is not in the manifest, or when the gate has no
            ``conditions`` field, or when no condition carries a
            ``predicate_refs`` list.  The caller interprets ``None`` as
            "Approach A fallback".
        """
        gate = self._gate_index.get(gate_id)
        if gate is None:
            return None

        conditions = gate.get("conditions") or []
        pred_ids: list[str] = []
        for condition in conditions:
            if isinstance(condition, dict):
                refs = condition.get("predicate_refs") or []
                pred_ids.extend(str(r) for r in refs)

        return pred_ids if pred_ids else None

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def gate_ids(self) -> list[str]:
        """Return all gate IDs present in the manifest (insertion order)."""
        return [
            g["gate_id"]
            for g in self._data.get("gate_registry", [])
            if isinstance(g, dict) and "gate_id" in g
        ]

    def has_predicate_refs(self, gate_id: str) -> bool:
        """Return ``True`` if the gate has at least one condition with predicate_refs."""
        return self.get_predicate_refs(gate_id) is not None
