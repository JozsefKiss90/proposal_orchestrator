"""R3 — the old-account id guard (``tools/old_id_guard.py``).

Acceptance, from ``plans/aws_redeployment_tickets.md`` R3: "The old-ID test
fails on a planted old id and passes on the real tree." Per the R3 handoff
(``plans/aws_redeployment_r3_handoff_2026-10-22.md`` §2), the guard matches
the exact old ids, never a prefix pattern, and covers the whole old-to-new map
of ``plans/aws_redeployment_handoff_2026-10-21.md`` §9.

The planted ids come from the guard module itself, so this file never holds
an old id. The new-account ids below are legitimate R1 evidence values that a
prefix pattern would wrongly refuse.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools import old_id_guard as guard

HANDOFF = Path("plans") / "aws_redeployment_handoff_2026-10-21.md"

NEW_ACCOUNT_IDS = [
    "797661577394",  # the new account
    "vpc-0fcb706a089aeb352",  # eu-north-1 default VPC (R1 evidence)
    "sg-085c137a9e87fc7ba",  # deleted Explore AWS security group (R1 evidence)
]


def _clean_tree(root: Path) -> Path:
    folder = root / "R4"
    folder.mkdir()
    (folder / "R4_01_vpc.json").write_text(
        '{"Vpcs": [{"VpcId": "%s", "OwnerId": "%s"}]}\n' % (NEW_ACCOUNT_IDS[1], NEW_ACCOUNT_IDS[0]),
        encoding="utf-8",
    )
    (folder / "RUNLOG.md").write_text(f"| 01 | deleted {NEW_ACCOUNT_IDS[2]} |\n", encoding="utf-8")
    return folder


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    end = text.index("\n## ", start + len(heading))
    return text[start:end]


# --- planted ids are refused --------------------------------------------------


@pytest.mark.parametrize("label", sorted(guard.OLD_IDS))
def test_guard_refuses_each_planted_old_id(tmp_path: Path, label: str) -> None:
    folder = _clean_tree(tmp_path)
    planted = folder / "R4_02_planted.json"
    planted.write_text(f'first line\n"Name": "x-{guard.OLD_IDS[label]}-y"\n', encoding="utf-8")

    findings = guard.scan_paths([folder])

    assert [(f.path.name, f.line, f.label) for f in findings] == [("R4_02_planted.json", 2, label)]
    assert guard.main([str(folder)]) == 1


def test_guard_reads_utf16_powershell_output(tmp_path: Path) -> None:
    folder = _clean_tree(tmp_path)
    old_host = guard.OLD_IDS["old host"]
    (folder / "R4_03_ps51.txt").write_bytes(("﻿" + f"InstanceId {old_host}\r\n").encode("utf-16-le"))

    assert [f.label for f in guard.scan_paths([folder])] == ["old host"]


def test_finding_names_the_label_not_the_id(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = _clean_tree(tmp_path)
    (folder / "R4_04_planted.txt").write_text(guard.OLD_IDS["old account"] + "\n", encoding="utf-8")

    assert guard.main([str(folder)]) == 1
    out = capsys.readouterr().out
    assert "old account" in out
    assert guard.OLD_IDS["old account"] not in out


# --- exact match, not prefix --------------------------------------------------


def test_new_account_ids_of_the_same_shape_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = _clean_tree(tmp_path)

    assert guard.scan_paths([folder]) == []
    assert guard.main([str(folder)]) == 0
    assert "CLEAN" in capsys.readouterr().out


def test_a_truncated_old_id_is_not_a_finding(tmp_path: Path) -> None:
    folder = _clean_tree(tmp_path)
    (folder / "R4_05_prefix.txt").write_text(guard.OLD_IDS["old host"][:-1] + "\n", encoding="utf-8")

    assert guard.scan_paths([folder]) == []


# --- the id list ----------------------------------------------------------------


def test_guard_covers_every_old_id_of_the_handoff_map() -> None:
    section = _section(HANDOFF.read_text(encoding="utf-8"), "## 9. Old-to-new resource map")
    old_column = []
    for row in section.splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] not in ("Logical resource", "---"):
            old_column.append(cells[1])
    pattern = re.compile(
        r"(?:vpc|subnet|rtb|sg|vpce|fl|i|pl)-[0-9a-f]{8,17}"
        r"|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        r"|(?<![0-9])[0-9]{12}(?![0-9])"
    )
    listed = {match for cell in old_column for match in pattern.findall(cell)}

    assert len(listed) >= 18
    assert listed <= set(guard.OLD_IDS.values())


def test_guard_covers_the_f7_security_group_rule() -> None:
    text = HANDOFF.read_text(encoding="utf-8")
    f7 = text[text.index("### F7.") : text.index("### F8.")]

    assert set(re.findall(r"sgr-[0-9a-f]{17}", f7)) <= set(guard.OLD_IDS.values())


def test_ticket_minimum_kinds_are_covered() -> None:
    values = list(guard.OLD_IDS.values())
    for prefix in ("vpce-", "sg-", "subnet-", "i-"):
        assert any(v.startswith(prefix) for v in values), prefix
    assert any(re.fullmatch(r"[0-9]{12}", v) for v in values)


def test_guard_module_is_not_itself_a_finding() -> None:
    assert guard.scan_paths([Path("tools") / "old_id_guard.py"]) == []


# --- the real tree --------------------------------------------------------------


def test_default_scope_is_the_v2_side_only() -> None:
    assert guard.DEFAULT_SCOPE == (
        "deploy/aws",
        "docs/infrastructure_security/evidence_v2",
        "docs/infrastructure_security/aws_hardening_control_register_v2.md",
        "docs/infrastructure_security/aws_hardening_worklog_v2.md",
        "docs/tier4_orchestration_state/decision_log/aws-redeployment-*.json",
    )


def test_real_tree_is_clean() -> None:
    findings = guard.scan_paths(guard.default_scope(Path.cwd()))

    assert [f.describe(Path.cwd()) for f in findings] == []


def test_missing_path_is_an_error_not_clean(tmp_path: Path) -> None:
    assert guard.main([str(tmp_path / "no-such-folder")]) == 2


def test_default_scope_glob_that_matches_nothing_is_an_error(tmp_path: Path) -> None:
    for entry in guard.DEFAULT_SCOPE:
        if "*" not in entry:
            target = tmp_path / entry
            if target.suffix:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("", encoding="utf-8")
            else:
                target.mkdir(parents=True, exist_ok=True)

    with pytest.raises(FileNotFoundError, match="matched nothing"):
        guard.default_scope(tmp_path)
