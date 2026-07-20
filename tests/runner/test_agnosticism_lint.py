"""
Tests for the "no project nouns" agnosticism lint (milestone 2, ticket 9).

Two layers:

* **Contract on the pure matcher / enumerator** — word-boundary + case-insensitive
  matching (``ELTE`` never hits ``Svelte``; ``crop`` never hits ``cropland`` or
  ``AquaCrop``), generic words are never flagged, the ``.obsidian`` vendored dir is
  excluded, and the report/CLI fail on a planted noun.
* **The test-of-done itself** — :func:`lint_generic_layer` over the *real* repo
  reports ``ok`` (the generic graph layer carries no instance-#1 project noun),
  scanning a non-vacuous, known-good file set.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runner.agnosticism_lint import (
    GENERIC_LAYER_GLOBS,
    PROJECT_NOUNS,
    TICKET_NAMED_NOUNS,
    LintReport,
    LintViolation,
    _is_excluded,
    format_report,
    iter_generic_layer_files,
    lint_generic_layer,
    main,
    scan_text,
)

# The repo root: this file is tests/runner/test_agnosticism_lint.py.
REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# scan_text — the pure matcher
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("noun", sorted(TICKET_NAMED_NOUNS))
def test_scan_flags_each_ticket_named_noun(noun: str) -> None:
    hits = scan_text(f"a line mentioning {noun} in prose")
    assert [h[1].lower() for h in hits] == [noun.lower()]


@pytest.mark.parametrize(
    "noun",
    [
        "AgroVIR",
        "ELTE",
        "Cholakova",
        "Jung",
        "Budapest",
        "Hungary",
        "Hungarian",
        "Bulgaria",
        "tomato",
        "AquaCrop",
    ],
)
def test_scan_flags_proper_and_domain_nouns(noun: str) -> None:
    assert scan_text(f"context {noun} context")
    # and it is in the published denylist
    assert noun in PROJECT_NOUNS


def test_scan_is_case_insensitive() -> None:
    for variant in ("MSCA", "msca", "Msca", "mScA"):
        hits = scan_text(f"the {variant} instrument")
        assert len(hits) == 1
        assert hits[0][1] == variant  # reported verbatim as it appears


def test_scan_respects_word_boundaries() -> None:
    # 'ELTE' must not hit inside 'Svelte'; 'crop' must not hit 'cropland' or the
    # brand 'AquaCrop' (AquaCrop is itself a noun, but not via a bare 'crop' hit).
    assert scan_text("built with the Svelte framework") == []
    assert scan_text("acres of cropland and microcrops") == []
    assert [h[1] for h in scan_text("the AquaCrop model")] == ["AquaCrop"]


def test_scan_does_not_flag_generic_words() -> None:
    generic = (
        "The objective, outcome, impact and partner are generic Horizon Europe "
        "nouns; the source-grounded budget and work package are too."
    )
    assert scan_text(generic) == []


def test_scan_reports_line_numbers_in_order() -> None:
    text = "clean line one\nmentions crop here\nclean\nand AgroVIR there\n"
    hits = scan_text(text)
    assert [(h[0], h[1]) for h in hits] == [(2, "crop"), (4, "AgroVIR")]
    # snippet is the stripped offending line
    assert hits[0][2] == "mentions crop here"


def test_ticket_named_nouns_are_in_the_denylist() -> None:
    # The three nouns the ticket names outright must be covered.
    assert TICKET_NAMED_NOUNS <= PROJECT_NOUNS
    assert {"MSCA", "crop", "irrigation"} <= PROJECT_NOUNS


# ---------------------------------------------------------------------------
# Exclusion + enumeration
# ---------------------------------------------------------------------------


def test_is_excluded() -> None:
    assert _is_excluded([".obsidian", "plugins", "dataview"])
    assert _is_excluded(["templates", "x", ".obsidian", "y.md"])
    assert not _is_excluded(["runner", "graph_compiler.py"])
    assert not _is_excluded(["templates", "obsidian_graph_vault", "vault", "n.md"])


def _plant(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_iter_filters_suffix_and_excludes_obsidian(tmp_path: Path) -> None:
    # Authored generic-layer files (scanned):
    _plant(tmp_path, "runner/graph_toy.py", "# clean\n")
    _plant(tmp_path, "templates/obsidian_graph_vault/vault/11_x/Node.md", "clean\n")
    _plant(tmp_path, ".claude/skills/obsidian-graph/SKILL.md", "clean\n")
    # Not scanned: wrong suffix, and a nested vendored .obsidian dir under vault.
    _plant(tmp_path, "runner/graph_asset.json", "irrelevant\n")
    _plant(
        tmp_path,
        "templates/obsidian_graph_vault/vault/.obsidian/plugins/x.md",
        "MSCA leak that must be ignored\n",
    )

    found = {p.relative_to(tmp_path).as_posix() for p in iter_generic_layer_files(tmp_path)}
    assert "runner/graph_toy.py" in found
    assert "templates/obsidian_graph_vault/vault/11_x/Node.md" in found
    assert ".claude/skills/obsidian-graph/SKILL.md" in found
    assert "runner/graph_asset.json" not in found  # wrong suffix
    assert all(".obsidian" not in f for f in found)  # vendored excluded


# ---------------------------------------------------------------------------
# lint_generic_layer on a synthetic tree — the fail direction
# ---------------------------------------------------------------------------


def test_lint_flags_planted_noun(tmp_path: Path) -> None:
    _plant(tmp_path, "runner/vault_reader.py", "clean substrate\n")
    _plant(
        tmp_path,
        "runner/graph_compiler.py",
        "# line one\n# the current MSCA vault leaked in\n",
    )
    report = lint_generic_layer(tmp_path)
    assert not report.ok
    assert len(report.violations) == 1
    v = report.violations[0]
    assert v == LintViolation(
        path="runner/graph_compiler.py",
        line=2,
        noun="MSCA",
        snippet="# the current MSCA vault leaked in",
    )
    # format_report surfaces the actionable file:line:noun.
    rendered = format_report(report)
    assert "runner/graph_compiler.py:2" in rendered and "'MSCA'" in rendered


def test_lint_clean_tree_is_ok(tmp_path: Path) -> None:
    _plant(tmp_path, "runner/graph_schema.py", "generic objective outcome impact\n")
    _plant(tmp_path, "runner/vault_reader.py", "generic partner and budget\n")
    report = lint_generic_layer(tmp_path)
    assert report.ok
    assert format_report(report).startswith("[agnosticism-lint] OK")


# ---------------------------------------------------------------------------
# THE test-of-done — the real generic layer is noun-free
# ---------------------------------------------------------------------------


def test_real_generic_layer_has_no_project_nouns() -> None:
    """§2.7 test-of-done: the shipped generic graph layer carries no project noun."""
    report = lint_generic_layer(REPO_ROOT)
    # Non-vacuous: the globs actually matched the known generic-layer sources.
    assert report.scanned_files, "lint scanned nothing — a glob is broken"
    for expected in (
        "runner/graph_compiler.py",
        "runner/graph_schema.py",
        "runner/vault_reader.py",
        "templates/obsidian_graph_vault/graph.config.yaml",
        ".claude/skills/obsidian-graph/SKILL.md",
    ):
        assert expected in report.scanned_files, f"{expected} not scanned"
    # The whole point: no leaks.
    assert report.ok, format_report(report)


def test_generic_layer_globs_are_declared() -> None:
    # Guard: the scope constant is the documented set (schema/reader/compiler +
    # template + skill), so a scope regression is visible in the diff.
    assert "runner/graph_*.py" in GENERIC_LAYER_GLOBS
    assert "runner/vault_*.py" in GENERIC_LAYER_GLOBS
    assert ".claude/skills/obsidian-graph/SKILL.md" in GENERIC_LAYER_GLOBS


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_main_returns_zero_on_clean_tree(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    _plant(tmp_path, "runner/graph_schema.py", "clean\n")
    assert main(["--repo-root", str(tmp_path)]) == 0
    assert "OK" in capsys.readouterr().out


def test_main_returns_one_on_planted_noun(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    _plant(tmp_path, "runner/graph_schema.py", "leak: irrigation decision support\n")
    assert main(["--repo-root", str(tmp_path)]) == 1
    assert "FAIL" in capsys.readouterr().err


def test_main_on_real_repo_is_clean() -> None:
    assert main(["--repo-root", str(REPO_ROOT)]) == 0
