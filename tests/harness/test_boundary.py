"""
Architectural boundary tests for the harness package.

The harness is out-of-band: it may import ``runner`` (to reuse the transport and
read the deterministic predicate registry), but ``runner`` must NEVER import
``harness`` — that one-way dependency is what makes "the harness is never a
runtime gate" a structural fact. If this test ever fails, an eval concern has
leaked into the runtime and the load-bearing invariant is broken.

Also asserts the package imports cleanly and re-exports its public API.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from runner.paths import find_repo_root

_IMPORT_HARNESS = re.compile(r"^\s*(?:from|import)\s+harness\b", re.MULTILINE)


class TestOneWayDependency:
    def test_runner_never_imports_harness(self):
        repo = find_repo_root()
        offenders: list[str] = []
        for py in (repo / "runner").rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if _IMPORT_HARNESS.search(text):
                offenders.append(str(py.relative_to(repo)))
        assert not offenders, (
            "runner must not import harness (out-of-band boundary); offenders: "
            + ", ".join(offenders)
        )

    def test_tools_and_scripts_do_not_import_harness_into_runtime(self):
        # The auxiliary runtime surfaces (tools/, scripts/) must stay harness-free
        # too — nothing that runs as part of producing the pipeline may depend on
        # the out-of-band eval layer.
        repo = find_repo_root()
        offenders: list[str] = []
        for sub in ("tools", "scripts"):
            base = repo / sub
            if not base.is_dir():
                continue
            for py in base.rglob("*.py"):
                if _IMPORT_HARNESS.search(py.read_text(encoding="utf-8")):
                    offenders.append(str(py.relative_to(repo)))
        assert not offenders, (
            "tools/ and scripts/ must not import harness (out-of-band boundary); "
            "offenders: " + ", ".join(offenders)
        )


class TestPackageSurface:
    def test_imports_clean(self):
        import harness  # noqa: F401

    def test_public_api_exported(self):
        import harness

        for name in (
            "Judge",
            "JudgeConfig",
            "Verdict",
            "MajorityVerdict",
            "majority_vote",
            "ProvenanceRecord",
            "ProvenanceLog",
            "prompt_hash",
            "route",
            "assert_judgeable",
            "HarnessReport",
            "build_report",
            "EVIDENCE_TYPE_INFERRED",
            # E1.5 calibration
            "GoldPair",
            "GoldSet",
            "load_gold_set",
            "seed_pairs_from_claim_statuses",
            "build_faithfulness_prompt",
            "calibrate",
            "calibrate_with_judge",
            "graduation_for",
            "CalibrationLog",
            "GraduationThreshold",
        ):
            assert hasattr(harness, name), name

    def test_harness_md_exists(self):
        repo = find_repo_root()
        assert (repo / "harness" / "HARNESS.md").is_file()


class TestHarnessCommands:
    """The former ``scripts/`` harness runners live behind harness module commands
    (``py -3.10 -m harness.commands.<name>``) so the runtime surfaces never
    depend on the eval layer."""

    from harness.commands import __all__ as COMMANDS

    @pytest.mark.parametrize("name", COMMANDS)
    def test_command_module_exposes_main(self, name):
        import importlib

        mod = importlib.import_module(f"harness.commands.{name}")
        assert callable(getattr(mod, "main", None)), name

    @pytest.mark.parametrize("name", COMMANDS)
    def test_command_not_left_under_scripts(self, name):
        repo = find_repo_root()
        assert not (repo / "scripts" / f"{name}.py").exists(), name
