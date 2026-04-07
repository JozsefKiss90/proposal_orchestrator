"""
Gate rules library loader.

Loads, validates, and provides gate lookup for
``.claude/workflows/system_orchestration/gate_rules_library.yaml``.

The library maps each ``gate_id`` to an ordered list of executable predicates.
The runner calls :meth:`GateLibrary.load` once at evaluation time and then uses
:meth:`GateLibrary.get_gate` to retrieve individual gate entries.

See gate_rules_library_plan.md §2 for the library file specification.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from runner.versions import MANIFEST_VERSION

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Repo-relative path to the gate rules library YAML.
LIBRARY_REL_PATH: str = (
    ".claude/workflows/system_orchestration/gate_rules_library.yaml"
)

#: Required top-level keys in the library YAML.
_REQUIRED_TOP_LEVEL: frozenset[str] = frozenset(
    {"library_version", "manifest_version", "constitution_version", "gate_rules"}
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GateLibraryError(Exception):
    """Raised for library loading or structural validation errors."""


class ManifestVersionMismatchError(GateLibraryError):
    """
    Raised when the library's ``manifest_version`` does not match the running
    manifest version.

    The runner must refuse to evaluate gates under a mismatched library
    (gate_rules_library_plan.md §2).
    """


class GateNotFoundError(GateLibraryError):
    """Raised when a requested ``gate_id`` is not present in the library."""


# ---------------------------------------------------------------------------
# GateLibrary
# ---------------------------------------------------------------------------


class GateLibrary:
    """
    In-memory representation of the loaded and validated gate rules library.

    Instances are created via :meth:`load`; direct construction is for
    testing only.
    """

    def __init__(self, data: dict) -> None:
        self._data: dict = data
        # Build an O(1) lookup index keyed by gate_id
        self._index: dict[str, dict] = {
            gate["gate_id"]: gate for gate in data.get("gate_rules", [])
        }
        # Build an O(1) lookup index keyed by predicate_id across all gates.
        # Used by Approach B: the runner resolves predicate_id → full predicate
        # entry after reading predicate_refs from the manifest.
        self._predicate_index: dict[str, dict] = {}
        for gate in data.get("gate_rules", []):
            for pred in gate.get("predicates") or []:
                pid = pred.get("predicate_id")
                if pid:
                    self._predicate_index[pid] = pred

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        library_path: Optional[Path] = None,
        *,
        repo_root: Optional[Path] = None,
        expected_manifest_version: str = MANIFEST_VERSION,
    ) -> "GateLibrary":
        """
        Load and validate the gate rules library from disk.

        Parameters
        ----------
        library_path:
            Explicit path to the YAML file.  When ``None``, resolves to
            ``repo_root / LIBRARY_REL_PATH``.  If ``repo_root`` is also
            ``None``, auto-discovers the repository root via
            :func:`runner.paths.find_repo_root`.
        repo_root:
            Repository root.  Used only when *library_path* is ``None``.
        expected_manifest_version:
            The manifest version the running system was compiled against.
            Defaults to :data:`runner.versions.MANIFEST_VERSION`.  A
            mismatch raises :exc:`ManifestVersionMismatchError`.

        Raises
        ------
        GateLibraryError
            File not found, invalid YAML, or missing required fields.
        ManifestVersionMismatchError
            Library ``manifest_version`` ≠ *expected_manifest_version*.
        GateNotFoundError
            (Not raised here — raised on subsequent :meth:`get_gate` calls.)
        """
        if library_path is None:
            if repo_root is None:
                from runner.paths import find_repo_root
                repo_root = find_repo_root()
            library_path = repo_root / LIBRARY_REL_PATH

        if not library_path.exists():
            raise GateLibraryError(
                f"Gate rules library not found: {library_path}"
            )

        try:
            raw_text = library_path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise GateLibraryError(
                f"Cannot read gate rules library {library_path}: {exc}"
            ) from exc

        try:
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            raise GateLibraryError(
                f"Invalid YAML in gate rules library {library_path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise GateLibraryError(
                f"Gate rules library root must be a YAML mapping; "
                f"got {type(data).__name__}"
            )

        missing_fields = _REQUIRED_TOP_LEVEL - data.keys()
        if missing_fields:
            raise GateLibraryError(
                f"Gate rules library is missing required top-level fields: "
                f"{sorted(missing_fields)}"
            )

        lib_manifest_version = str(data["manifest_version"])
        if lib_manifest_version != expected_manifest_version:
            raise ManifestVersionMismatchError(
                f"Library manifest_version {lib_manifest_version!r} does not "
                f"match running manifest version {expected_manifest_version!r}.  "
                "Rebuild the library against the current manifest before running "
                "gate evaluation."
            )

        gate_rules = data["gate_rules"]
        if not isinstance(gate_rules, list):
            raise GateLibraryError(
                "'gate_rules' must be a YAML sequence (list of gate entries)"
            )

        for i, gate in enumerate(gate_rules):
            if not isinstance(gate, dict):
                raise GateLibraryError(
                    f"gate_rules[{i}] must be a mapping; got {type(gate).__name__}"
                )
            if "gate_id" not in gate:
                raise GateLibraryError(
                    f"gate_rules[{i}] is missing required field 'gate_id'"
                )
            if "gate_kind" not in gate:
                gate_id_hint = gate.get("gate_id", f"index {i}")
                raise GateLibraryError(
                    f"gate_rules entry for {gate_id_hint!r} is missing required "
                    "field 'gate_kind'"
                )

        return cls(data)

    # ------------------------------------------------------------------
    # Gate lookup
    # ------------------------------------------------------------------

    def get_gate(self, gate_id: str) -> dict:
        """
        Return the gate entry dict for *gate_id*.

        Raises
        ------
        GateNotFoundError
            If *gate_id* is not present in the library.
        """
        if gate_id not in self._index:
            raise GateNotFoundError(
                f"gate_id {gate_id!r} not found in the gate rules library.  "
                f"Available gates: {sorted(self._index)}"
            )
        return self._index[gate_id]

    def get_predicate(self, predicate_id: str) -> dict:
        """
        Return the predicate entry dict for *predicate_id*.

        Used by Approach B gate evaluation: the runner reads ``predicate_refs``
        from the manifest, then resolves each ID here to obtain the full
        predicate definition (type, function, args, fail_message,
        prose_condition).

        Raises
        ------
        GateLibraryError
            If *predicate_id* is not found in any gate in the library.
        """
        if predicate_id not in self._predicate_index:
            raise GateLibraryError(
                f"predicate_id {predicate_id!r} not found in any gate in the "
                f"gate rules library."
            )
        return self._predicate_index[predicate_id]

    # ------------------------------------------------------------------
    # Version properties
    # ------------------------------------------------------------------

    @property
    def library_version(self) -> str:
        """Library version string from the YAML header."""
        return str(self._data["library_version"])

    @property
    def manifest_version(self) -> str:
        """Manifest version string from the YAML header."""
        return str(self._data["manifest_version"])

    @property
    def constitution_version(self) -> str:
        """Constitution version (git SHA or date-stamp) from the YAML header."""
        return str(self._data["constitution_version"])

    # ------------------------------------------------------------------
    # Iteration helpers
    # ------------------------------------------------------------------

    def gate_ids(self) -> list[str]:
        """Return all gate IDs present in the library (insertion order)."""
        return [gate["gate_id"] for gate in self._data.get("gate_rules", [])]
