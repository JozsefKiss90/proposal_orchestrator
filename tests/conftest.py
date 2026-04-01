"""
Session-scoped fixtures shared across all test modules.
"""

import pytest
from pathlib import Path

from runner.paths import find_repo_root


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repository root (contains CLAUDE.md and .git/)."""
    return find_repo_root()
