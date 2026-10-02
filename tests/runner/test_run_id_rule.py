"""The run id rule, and the CLI entry point that enforces it.

A run id is used as a directory name under ``.claude/runs`` and nothing used
to validate it: a mis-pasted shell command became a run directory, and the
shadow comparison's reader could then never name that run. The rule has one
owner, ``runner.run_context``, and the CLI rejects an id that breaks it
before any run directory exists. The DAG scheduler is not touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.run_context import (
    PRESERVED_RUN_RECORD_SCHEMA_ID,
    PRESERVED_RUN_RECORDS_REL,
    RUN_ID_RULE,
    RUNS_DIR_REL,
    is_plain_run_id,
    run_id_slug,
)

MISPASTED = "import uuid; print(uuid.uuid4())"


class TestTheRule:
    @pytest.mark.parametrize(
        "run_id",
        [
            "d68acaef-e9b2-412e-bc09-4b34c386d5fd",
            "test-00000000-0000-0000-0000-000000000000",
            "cli-test",
            "run_01.a",
            "0",
        ],
    )
    def test_plain_identifiers_pass(self, run_id: str) -> None:
        assert is_plain_run_id(run_id)

    @pytest.mark.parametrize(
        "run_id",
        [MISPASTED, "", " ", "bad id", "-leading-dash", ".hidden", "a/b", "a\\b", "a;b", None, 7],
    )
    def test_anything_else_fails(self, run_id: object) -> None:
        assert not is_plain_run_id(run_id)  # type: ignore[arg-type]

    def test_the_rule_is_stated_for_the_operator(self) -> None:
        assert "letter" in RUN_ID_RULE and "digit" in RUN_ID_RULE

    def test_the_rule_matches_the_shadow_readers_rule(self) -> None:
        # The ticket asks for the same identifier rule in both places. The
        # reader imports the owner's rule, so the two cannot drift; this pins
        # that the import is still the mechanism.
        from runner.dev_graph import shadow

        assert shadow.is_plain_run_id is is_plain_run_id


class TestTheSlug:
    def test_a_plain_id_is_its_own_slug(self) -> None:
        assert run_id_slug("d68acaef-e9b2-412e-bc09-4b34c386d5fd") == "d68acaef-e9b2-412e-bc09-4b34c386d5fd"

    def test_the_mispasted_id_slugifies_to_its_preserved_file_name(self) -> None:
        # The name the preserve tool already wrote the record under.
        assert run_id_slug(MISPASTED) == "import-uuid-print-uuid.uuid4"

    def test_a_slug_is_always_a_plain_identifier(self) -> None:
        for raw in (MISPASTED, "---", "", "x" * 200, "a b/c\\d;e", ".hidden"):
            assert is_plain_run_id(run_id_slug(raw)), raw

    def test_the_preserved_layout_is_declared(self) -> None:
        assert PRESERVED_RUN_RECORDS_REL == "docs/tier4_orchestration_state/run_records"
        assert PRESERVED_RUN_RECORD_SCHEMA_ID == "orch.run_record.preserved.v1"


class TestTheEntryPoint:
    """``python -m runner --run-id <bad>`` fails before a directory exists."""

    def test_a_mispasted_run_id_is_rejected_with_the_rule_named(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from runner.__main__ import main

        code = main(["--run-id", MISPASTED, "--repo-root", str(tmp_path), "--dry-run"])

        assert code == 3
        err = capsys.readouterr().err
        assert "not a plain identifier" in err
        assert RUN_ID_RULE in err
        assert not (tmp_path / RUNS_DIR_REL).exists(), "a rejected id must never become a run directory"

    def test_the_rejection_is_reported_as_json_when_asked(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from runner.__main__ import main

        code = main(["--run-id", "bad id", "--repo-root", str(tmp_path), "--dry-run", "--json"])

        assert code == 3
        events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
        assert any(e["event"] == "error" and "not a plain identifier" in e["message"] for e in events)
        assert not (tmp_path / RUNS_DIR_REL).exists()
