"""
Consistency guard: ``skill_catalog.yaml`` must declare every input path that a
*live* skill's own ``.md`` spec declares in its front-matter ``reads_from``.

Why this exists
---------------
The runtime (:mod:`runner.skill_runtime`) enforces the CATALOG's
``reads_from`` / ``optional_reads_from`` as the bounded set of paths a TAPM skill
is permitted to read. Each skill's ``.claude/skills/<id>.md`` *also* declares
``reads_from`` (front-matter) and describes the same inputs in prose -- but that
file is only what the model is *shown*, not what the runtime *enforces*. If the
catalog omits a path the skill needs, the skill is silently blocked from it and
fails at run time with a confusing ``MISSING_INPUT`` deep inside a Phase-8
drafting pass, far from the one-line cause.

That is exactly how ``proposal-section-traceability-check`` failed: its catalog
listed only Tier 5 while its ``.md``, correctly, listed Tier 1-4. The two
hand-maintained copies had drifted, and nothing caught it until a live run.

This guard turns that drift into a loud failure here instead of a silent one at
run time. For every *live* skill (one that at least one agent uses) that has a
flat ``.md`` spec, it asserts::

    catalog.reads_from  U  catalog.optional_reads_from   >=   spec.reads_from

A spec path ``P`` is *covered* by a catalog path ``C`` when, after stripping
trailing slashes, ``P == C`` or ``P`` lies under directory ``C``
(``P.startswith(C + "/")``). Contextual descriptors (entries containing a space,
matching :func:`runner.skill_runtime._is_contextual_descriptor`) are ignored, as
are skills with an empty ``used_by_agents`` -- superseded skills whose empty
``reads_from`` is an intentional signal (e.g. ``proposal-section-drafting``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from runner.paths import find_repo_root

_CATALOG_REL = ".claude/workflows/system_orchestration/skill_catalog.yaml"
_SKILLS_DIR_REL = ".claude/skills"


def _catalog_entries(repo_root: Path) -> dict[str, dict]:
    data = yaml.safe_load(
        (repo_root / _CATALOG_REL).read_text(encoding="utf-8-sig")
    )
    entries = data.get("skill_catalog", [])
    assert isinstance(entries, list) and entries, "skill_catalog.yaml empty/invalid"
    return {e["id"]: e for e in entries if isinstance(e, dict) and "id" in e}


def _spec_frontmatter(md_path: Path) -> dict:
    lines = md_path.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}
    data = yaml.safe_load("\n".join(lines[1:end])) or {}
    return data if isinstance(data, dict) else {}


def _is_live(entry: dict) -> bool:
    agents = entry.get("used_by_agents") or []
    return isinstance(agents, list) and len(agents) > 0


def _is_contextual(entry: str) -> bool:
    # A reads_from entry containing a space is a prose input hint, not a file path
    # (mirrors runner.skill_runtime._is_contextual_descriptor).
    return " " in entry


def _norm(p: str) -> str:
    return p.rstrip("/")


def _covered(spec_path: str, catalog_paths: set[str]) -> bool:
    p = _norm(spec_path)
    return any(p == c or p.startswith(c + "/") for c in catalog_paths)


def _live_skills_with_specs() -> list[str]:
    try:
        repo_root = find_repo_root()
        skills = repo_root / _SKILLS_DIR_REL
        return [
            sid
            for sid, entry in _catalog_entries(repo_root).items()
            if _is_live(entry) and (skills / f"{sid}.md").is_file()
        ]
    except Exception:  # never hard-crash collection; the vacuity guard below catches it
        return []


@pytest.mark.parametrize("skill_id", _live_skills_with_specs())
def test_catalog_declares_everything_the_spec_reads(skill_id: str) -> None:
    repo_root = find_repo_root()
    entry = _catalog_entries(repo_root)[skill_id]
    spec = _spec_frontmatter(repo_root / _SKILLS_DIR_REL / f"{skill_id}.md")

    catalog_paths = {
        _norm(p)
        for key in ("reads_from", "optional_reads_from")
        for p in (entry.get(key) or [])
        if isinstance(p, str) and not _is_contextual(p)
    }
    spec_paths = [
        p
        for p in (spec.get("reads_from") or [])
        if isinstance(p, str) and not _is_contextual(p)
    ]

    missing = [p for p in spec_paths if not _covered(p, catalog_paths)]
    assert not missing, (
        f"skill_catalog.yaml entry {skill_id!r} does not declare input path(s) "
        f"that its .md spec's reads_from requires: {missing}. The runtime enforces "
        f"the catalog (not the .md), so the skill is blocked from these at run time "
        f"(MISSING_INPUT). Add them to reads_from/optional_reads_from in "
        f"skill_catalog.yaml -- or, if the skill no longer reads them, trim the .md."
    )


def test_consistency_guard_is_not_vacuous() -> None:
    # If parametrization silently became empty (e.g. a moved path), the guard would
    # check nothing while appearing to pass. Fail loudly instead.
    assert _live_skills_with_specs(), (
        "No live catalog skills with .md specs found -- the consistency guard would "
        "be checking nothing. Verify the catalog / .claude/skills/ paths."
    )
