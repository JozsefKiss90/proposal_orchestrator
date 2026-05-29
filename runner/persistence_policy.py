"""
Environment-scoped persistence policy for diagnostic files.

Controls what diagnostic data is persisted to disk based on the deployment
environment (development, staging, production).  This module is the sole
authority for persistence-level decisions across the runtime.

Policy matrix:

    +-------------+----------------------------+-----------------------------------+
    | Environment | ORCHESTRATOR_DIAGNOSTIC_   | Behavior                          |
    |             | LEVEL                      |                                   |
    +-------------+----------------------------+-----------------------------------+
    | Development | unset or "full"            | Full: response text, prompts on   |
    |             |                            | failure, parsed output. Current   |
    |             |                            | behavior preserved unchanged.     |
    +-------------+----------------------------+-----------------------------------+
    | Development | "metadata"                 | Metadata only: char counts,       |
    |             |                            | timing, error class. No prompt/   |
    |             |                            | response content written.         |
    +-------------+----------------------------+-----------------------------------+
    | Production  | unset                      | Defaults to "metadata". Full      |
    |             |                            | content never written.            |
    +-------------+----------------------------+-----------------------------------+
    | Production  | "full"                     | REJECTED. Raises ValueError at    |
    |             |                            | policy resolution time.           |
    +-------------+----------------------------+-----------------------------------+
    | Production  | "metadata"                 | Metadata only. Explicit.          |
    +-------------+----------------------------+-----------------------------------+

File-level behavior under each diagnostic level:

    +-------------------------------------------+-------+----------+
    | File                                      | full  | metadata |
    +-------------------------------------------+-------+----------+
    | {skill}_{run}_response.txt                | YES   | NO       |
    | {skill}_{run}_parsed.txt                  | YES   | NO       |
    | {skill}_{run}_phase_e.txt (no content)    | YES   | YES      |
    | {skill}_{run}_transport_diag.json (meta)  | YES   | YES      |
    | {skill}_{run}_system_prompt.txt           | YES   | NO       |
    | {skill}_{run}_user_prompt.txt             | YES   | NO       |
    | {skill}_{run}_stdout.txt                  | YES   | NO       |
    | {skill}_{run}_stderr.txt                  | YES   | NO       |
    | {func}_{run}_dispatch_meta.json (meta)    | YES   | YES      |
    | {func}_{run}_system_prompt.txt            | YES   | NO       |
    | {func}_{run}_user_prompt.txt              | YES   | NO       |
    | {func}_{run}_response.txt                 | YES   | NO       |
    | {func}_{run}_stderr.txt                   | YES   | NO       |
    | {func}_{run}_stdout.txt                   | YES   | NO       |
    | Benchmark ledger (invocation_ledger.jsonl) | YES   | YES      |
    | Run manifest / run_summary.json           | YES   | YES      |
    +-------------------------------------------+-------+----------+

Constitutional authority:
    Subordinate to CLAUDE.md and ``runner/transport/config.py`` (production
    mode enforcement).  This module does not modify transport behavior,
    gate logic, or artifact writes.  It only governs diagnostic file
    persistence.
"""

from __future__ import annotations

import logging
import os
from enum import Enum

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Valid diagnostic level values.
VALID_DIAGNOSTIC_LEVELS: frozenset[str] = frozenset({"full", "metadata"})

#: Maximum length for exception/error messages in metadata JSON files
#: under production mode.  Messages longer than this are truncated to
#: prevent prompt content leakage via error echoing.
PRODUCTION_ERROR_MESSAGE_MAX_LENGTH: int = 200


class DiagnosticLevel(Enum):
    """Diagnostic persistence level."""

    FULL = "full"
    METADATA = "metadata"


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_resolved_level: DiagnosticLevel | None = None
_resolved: bool = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_diagnostic_level() -> DiagnosticLevel:
    """Resolve the effective diagnostic level from environment variables.

    Uses ``ORCHESTRATOR_PRODUCTION_MODE`` and
    ``ORCHESTRATOR_DIAGNOSTIC_LEVEL`` to determine the persistence policy.

    Returns
    -------
    DiagnosticLevel
        The resolved diagnostic level.

    Raises
    ------
    ValueError
        If ``ORCHESTRATOR_PRODUCTION_MODE=true`` and
        ``ORCHESTRATOR_DIAGNOSTIC_LEVEL=full`` (policy violation).
    ValueError
        If ``ORCHESTRATOR_DIAGNOSTIC_LEVEL`` is set to an unrecognized value.
    """
    global _resolved_level, _resolved
    if _resolved:
        return _resolved_level  # type: ignore[return-value]

    from runner.transport.config import is_production_mode

    production = is_production_mode()
    raw_level = os.environ.get("ORCHESTRATOR_DIAGNOSTIC_LEVEL", "").strip().lower()

    if raw_level and raw_level not in VALID_DIAGNOSTIC_LEVELS:
        raise ValueError(
            f"ORCHESTRATOR_DIAGNOSTIC_LEVEL={raw_level!r} is not valid. "
            f"Valid values: {sorted(VALID_DIAGNOSTIC_LEVELS)}"
        )

    if production:
        if raw_level == "full":
            raise ValueError(
                "ORCHESTRATOR_PRODUCTION_MODE=true and "
                "ORCHESTRATOR_DIAGNOSTIC_LEVEL=full is a policy violation. "
                "Production mode does not allow full diagnostic persistence. "
                "Remove ORCHESTRATOR_DIAGNOSTIC_LEVEL or set it to 'metadata'."
            )
        # Production defaults to metadata regardless of whether explicitly set.
        level = DiagnosticLevel.METADATA
    else:
        # Development/staging: default to full (preserves current behavior).
        if raw_level == "metadata":
            level = DiagnosticLevel.METADATA
        else:
            level = DiagnosticLevel.FULL

    _resolved_level = level
    _resolved = True
    return level


def reset_diagnostic_level_cache() -> None:
    """Reset the cached diagnostic level.  For testing only."""
    global _resolved_level, _resolved
    _resolved_level = None
    _resolved = False


def allows_content_persistence() -> bool:
    """Return ``True`` if the current policy allows writing prompt/response content.

    This is the primary check used by diagnostic write functions.
    When ``False``, only metadata files (char counts, timing, error
    class) may be written.  Content files (prompts, responses, parsed
    output) must be skipped.
    """
    return resolve_diagnostic_level() == DiagnosticLevel.FULL


def allows_benchmark_persistence() -> bool:
    """Return ``True`` if benchmark telemetry persistence is allowed.

    Benchmark telemetry (invocation_ledger.jsonl) captures character
    counts, timing, and error class/message only --- never prompt or
    response content.  It is safe in all environments.
    """
    return True


def sanitize_error_message(message: str) -> str:
    """Sanitize an error/exception message for metadata persistence.

    In production mode (``ORCHESTRATOR_PRODUCTION_MODE=true``), truncates
    error messages to :data:`PRODUCTION_ERROR_MESSAGE_MAX_LENGTH` characters
    to prevent prompt content leakage through error echoing.

    In development mode, returns the message unchanged.

    Parameters
    ----------
    message : str
        The raw error or exception message.

    Returns
    -------
    str
        The sanitized message.
    """
    from runner.transport.config import is_production_mode

    if not is_production_mode():
        return message

    if len(message) <= PRODUCTION_ERROR_MESSAGE_MAX_LENGTH:
        return message

    return message[:PRODUCTION_ERROR_MESSAGE_MAX_LENGTH] + " [TRUNCATED]"
