"""
Unit tests for runner.predicates.file_predicates (Step 3).

Coverage:
    exists()          — §exists block
    non_empty()       — §non_empty block
    non_empty_json()  — §non_empty_json block
    dir_non_empty()   — §dir_non_empty block
    PredicateResult   — §types block
    repo-relative     — §repo_relative block

All tests use pytest's ``tmp_path`` fixture for isolated filesystem
state, except the repo-relative section which exercises real repository
paths to confirm that ``repo_root`` resolves correctly.
"""

import json
from pathlib import Path

import pytest

from runner.predicates.file_predicates import (
    dir_non_empty,
    exists,
    non_empty,
    non_empty_json,
)
from runner.predicates.types import (
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    PredicateResult,
)


# ===========================================================================
# Helpers
# ===========================================================================


def write(path: Path, content: str | bytes, *, encoding: str = "utf-8") -> Path:
    """Write *content* to *path* and return *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding=encoding)
    return path


# ===========================================================================
# §types — PredicateResult invariants
# ===========================================================================


class TestPredicateResultInvariants:
    def test_pass_no_category(self):
        r = PredicateResult(passed=True)
        assert r.passed is True
        assert r.failure_category is None
        assert r.reason is None
        assert r.details == {}

    def test_pass_with_details(self):
        r = PredicateResult(passed=True, details={"path": "/some/file.json"})
        assert r.passed is True
        assert r.details["path"] == "/some/file.json"

    def test_fail_requires_category(self):
        with pytest.raises(ValueError, match="failure_category"):
            PredicateResult(passed=False)

    def test_fail_rejects_unknown_category(self):
        with pytest.raises(ValueError, match="Unknown failure_category"):
            PredicateResult(passed=False, failure_category="INVENTED_CATEGORY")

    def test_fail_valid_category(self):
        r = PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason="file not found",
        )
        assert r.passed is False
        assert r.failure_category == MISSING_MANDATORY_INPUT
        assert r.reason == "file not found"

    def test_pass_with_category_raises(self):
        with pytest.raises(ValueError, match="failure_category"):
            PredicateResult(passed=True, failure_category=MISSING_MANDATORY_INPUT)

    def test_pass_with_reason_raises(self):
        with pytest.raises(ValueError, match="reason"):
            PredicateResult(passed=True, reason="should not be here")


# ===========================================================================
# §exists
# ===========================================================================


class TestExists:
    def test_existing_file_passes(self, tmp_path):
        f = write(tmp_path / "artifact.json", '{"key": "value"}')
        result = exists(f)
        assert result.passed is True
        assert result.details["is_file"] is True
        assert result.details["is_dir"] is False

    def test_existing_directory_passes(self, tmp_path):
        d = tmp_path / "some_dir"
        d.mkdir()
        result = exists(d)
        assert result.passed is True
        assert result.details["is_dir"] is True
        assert result.details["is_file"] is False

    def test_missing_path_fails(self, tmp_path):
        result = exists(tmp_path / "nonexistent.json")
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT
        assert result.reason is not None

    def test_details_contain_path(self, tmp_path):
        f = write(tmp_path / "f.json", "{}")
        result = exists(f)
        assert "path" in result.details

    def test_absolute_path(self, tmp_path):
        f = write(tmp_path / "abs.json", '{"x": 1}')
        result = exists(f.resolve())
        assert result.passed is True


# ===========================================================================
# §non_empty
# ===========================================================================


class TestNonEmpty:
    def test_non_empty_file_passes(self, tmp_path):
        f = write(tmp_path / "data.json", '{"a": 1}')
        result = non_empty(f)
        assert result.passed is True
        assert result.details["size_bytes"] > 0

    def test_zero_byte_file_fails_malformed(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_bytes(b"")
        result = non_empty(f)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert result.details["size_bytes"] == 0

    def test_directory_fails_malformed(self, tmp_path):
        d = tmp_path / "a_directory"
        d.mkdir()
        result = non_empty(d)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert result.details.get("is_dir") is True

    def test_missing_path_fails_missing(self, tmp_path):
        result = non_empty(tmp_path / "ghost.json")
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_one_byte_file_passes(self, tmp_path):
        f = tmp_path / "tiny.txt"
        f.write_bytes(b"x")
        result = non_empty(f)
        assert result.passed is True
        assert result.details["size_bytes"] == 1

    def test_details_contain_path(self, tmp_path):
        f = write(tmp_path / "d.json", '{"v": 1}')
        result = non_empty(f)
        assert "path" in result.details


# ===========================================================================
# §non_empty_json
# ===========================================================================


class TestNonEmptyJson:
    # --- passing cases ---

    def test_valid_object_passes(self, tmp_path):
        f = write(tmp_path / "obj.json", '{"key": "value", "count": 3}')
        result = non_empty_json(f)
        assert result.passed is True
        assert result.details["parsed_type"] == "dict"

    def test_valid_array_passes(self, tmp_path):
        f = write(tmp_path / "arr.json", '[1, 2, 3]')
        result = non_empty_json(f)
        assert result.passed is True
        assert result.details["parsed_type"] == "list"

    def test_valid_nested_object_passes(self, tmp_path):
        payload = json.dumps({"schema_id": "orch.phase3.wp_structure.v1", "run_id": "abc"})
        f = write(tmp_path / "wp.json", payload)
        result = non_empty_json(f)
        assert result.passed is True

    def test_scalar_string_passes(self, tmp_path):
        """
        A bare JSON string is not null, {}, or [].
        Per the literal contract it passes.  In practice canonical
        artifacts are always objects; this case should never arise.
        """
        f = write(tmp_path / "str.json", '"hello"')
        result = non_empty_json(f)
        assert result.passed is True
        assert result.details["parsed_type"] == "str"

    def test_scalar_number_passes(self, tmp_path):
        """Bare JSON integer: not null, {}, or []. Passes per contract."""
        f = write(tmp_path / "num.json", "42")
        result = non_empty_json(f)
        assert result.passed is True
        assert result.details["parsed_type"] == "int"

    def test_scalar_bool_passes(self, tmp_path):
        """Bare JSON boolean: not null, {}, or []. Passes per contract."""
        f = write(tmp_path / "bool.json", "true")
        result = non_empty_json(f)
        assert result.passed is True
        assert result.details["parsed_type"] == "bool"

    def test_scalar_zero_passes(self, tmp_path):
        """The integer 0 is falsy in Python but is not null, {}, or []."""
        f = write(tmp_path / "zero.json", "0")
        result = non_empty_json(f)
        assert result.passed is True

    # --- failing cases: MALFORMED_ARTIFACT ---

    def test_empty_object_fails(self, tmp_path):
        f = write(tmp_path / "empty_obj.json", "{}")
        result = non_empty_json(f)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "empty structured value" in result.reason

    def test_empty_array_fails(self, tmp_path):
        f = write(tmp_path / "empty_arr.json", "[]")
        result = non_empty_json(f)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "empty structured value" in result.reason

    def test_null_fails(self, tmp_path):
        f = write(tmp_path / "null.json", "null")
        result = non_empty_json(f)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "empty structured value" in result.reason

    def test_invalid_json_fails(self, tmp_path):
        f = write(tmp_path / "bad.json", "{key: value}")
        result = non_empty_json(f)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "Invalid JSON" in result.reason
        assert "json_error" in result.details

    def test_truncated_json_fails(self, tmp_path):
        f = write(tmp_path / "trunc.json", '{"key":')
        result = non_empty_json(f)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_empty_file_fails(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_bytes(b"")
        result = non_empty_json(f)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "empty" in result.reason.lower()

    def test_whitespace_only_file_fails(self, tmp_path):
        f = write(tmp_path / "ws.json", "   \n\t  ")
        result = non_empty_json(f)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "empty" in result.reason.lower()

    def test_directory_fails_malformed(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        result = non_empty_json(d)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert result.details.get("is_dir") is True

    def test_non_utf8_bytes_fails(self, tmp_path):
        f = tmp_path / "latin1.json"
        # Write bytes that are invalid UTF-8
        f.write_bytes(b'{"key": "\xff\xfe"}')
        result = non_empty_json(f)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_bom_prefixed_json_passes(self, tmp_path):
        """UTF-8 BOM should be stripped, not treated as a parse error."""
        content = '\ufeff{"schema_id": "orch.phase1.call_analysis_summary.v1"}'
        f = write(tmp_path / "bom.json", content)
        result = non_empty_json(f)
        assert result.passed is True

    # --- failing cases: MISSING_MANDATORY_INPUT ---

    def test_missing_file_fails_missing(self, tmp_path):
        result = non_empty_json(tmp_path / "absent.json")
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    # --- detail checks ---

    def test_details_contain_path_on_pass(self, tmp_path):
        f = write(tmp_path / "p.json", '{"x": 1}')
        result = non_empty_json(f)
        assert "path" in result.details

    def test_details_contain_path_on_fail(self, tmp_path):
        result = non_empty_json(tmp_path / "missing.json")
        assert "path" in result.details

    def test_json_error_details_on_parse_failure(self, tmp_path):
        f = write(tmp_path / "broken.json", "[1, 2,")
        result = non_empty_json(f)
        assert "error_line" in result.details
        assert "error_col" in result.details


# ===========================================================================
# §dir_non_empty
# ===========================================================================


class TestDirNonEmpty:
    def test_directory_with_one_file_passes(self, tmp_path):
        d = tmp_path / "sources"
        d.mkdir()
        write(d / "work_programme_2024.pdf", b"PDF content here")
        result = dir_non_empty(d)
        assert result.passed is True
        assert result.details["non_empty_file_count"] == 1

    def test_directory_with_multiple_files_passes(self, tmp_path):
        d = tmp_path / "extracted"
        d.mkdir()
        write(d / "a.json", '{"items": [1]}')
        write(d / "b.json", '{"items": [2]}')
        result = dir_non_empty(d)
        assert result.passed is True
        assert result.details["non_empty_file_count"] == 2

    def test_empty_directory_fails_missing(self, tmp_path):
        d = tmp_path / "empty_dir"
        d.mkdir()
        result = dir_non_empty(d)
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT
        assert result.details["non_empty_file_count"] == 0

    def test_directory_only_zero_byte_files_fails_missing(self, tmp_path):
        """
        Directory containing files that are all zero bytes fails.
        The required usable input (at least one non-empty file) is absent.
        """
        d = tmp_path / "zero_files"
        d.mkdir()
        (d / "placeholder.txt").write_bytes(b"")
        (d / "another.json").write_bytes(b"")
        result = dir_non_empty(d)
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT
        assert "zero bytes" in result.reason

    def test_directory_with_only_subdirectories_fails(self, tmp_path):
        """
        Non-recursive: subdirectories do not satisfy the predicate.
        """
        d = tmp_path / "parent"
        d.mkdir()
        (d / "subdir").mkdir()
        result = dir_non_empty(d)
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_file_path_fails_missing(self, tmp_path):
        """
        A file path given where a directory is expected: the required
        directory is absent.
        """
        f = write(tmp_path / "actually_a_file.json", '{"x": 1}')
        result = dir_non_empty(f)
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT
        assert result.details.get("is_file") is True

    def test_missing_path_fails_missing(self, tmp_path):
        result = dir_non_empty(tmp_path / "does_not_exist")
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_non_empty_file_count_in_details(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        write(d / "a.txt", b"content")
        write(d / "b.txt", b"more")
        (d / "empty.txt").write_bytes(b"")
        result = dir_non_empty(d)
        assert result.passed is True
        # empty.txt is excluded; only 2 non-empty files count
        assert result.details["non_empty_file_count"] == 2

    def test_details_contain_path(self, tmp_path):
        d = tmp_path / "d2"
        d.mkdir()
        write(d / "x.json", b"x")
        result = dir_non_empty(d)
        assert "path" in result.details

    def test_zero_byte_mixed_with_nonempty_passes(self, tmp_path):
        """One zero-byte and one non-empty: predicate passes."""
        d = tmp_path / "mixed"
        d.mkdir()
        (d / "placeholder").write_bytes(b"")
        write(d / "real.json", '{"data": true}')
        result = dir_non_empty(d)
        assert result.passed is True


# ===========================================================================
# §repo_relative — tests using actual repository paths
# ===========================================================================


class TestRepoRelativePaths:
    """
    Smoke tests confirming that repo_root-relative path resolution works
    against the actual repository.  These tests depend on repository
    structure; they verify integration of resolve_repo_path with the
    predicate layer.
    """

    def test_exists_on_claude_md(self, repo_root):
        """CLAUDE.md is guaranteed to exist at the repo root."""
        result = exists("CLAUDE.md", repo_root=repo_root)
        assert result.passed is True
        assert result.details["is_file"] is True

    def test_dir_non_empty_on_workflow_package(self, repo_root):
        """
        .claude/workflows/system_orchestration/ contains YAML source files
        and must be non-empty.
        """
        result = dir_non_empty(
            ".claude/workflows/system_orchestration",
            repo_root=repo_root,
        )
        assert result.passed is True
        assert result.details["non_empty_file_count"] > 0

    def test_non_empty_json_on_gate_rules_library_is_yaml_not_json(self, repo_root):
        """
        gate_rules_library.yaml is non-empty but is YAML, not JSON.
        Confirms non_empty_json correctly rejects non-JSON content as
        MALFORMED_ARTIFACT rather than silently passing.
        """
        result = non_empty_json(
            ".claude/workflows/system_orchestration/gate_rules_library.yaml",
            repo_root=repo_root,
        )
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_non_empty_json_on_manifest(self, repo_root):
        """
        manifest.compile.yaml is YAML; confirms same rejection behaviour
        for a second known repository file.
        """
        result = non_empty_json(
            ".claude/workflows/system_orchestration/manifest.compile.yaml",
            repo_root=repo_root,
        )
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_exists_on_missing_tier4_artifact(self, repo_root):
        """
        A canonical Tier 4 artifact that has not yet been produced is absent.
        Confirms that a repo-relative missing path returns MISSING_MANDATORY_INPUT.
        """
        result = exists(
            "docs/tier4_orchestration_state/phase_outputs/"
            "phase1_call_analysis/call_analysis_summary.json",
            repo_root=repo_root,
        )
        # Either the file exists (populated repo) or is absent — both are valid.
        # The key assertion is that the predicate returns a well-formed result.
        assert isinstance(result, PredicateResult)
        if not result.passed:
            assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_non_empty_on_claude_md(self, repo_root):
        """CLAUDE.md is a non-empty file at the repository root."""
        result = non_empty("CLAUDE.md", repo_root=repo_root)
        assert result.passed is True
        assert result.details["size_bytes"] > 0
