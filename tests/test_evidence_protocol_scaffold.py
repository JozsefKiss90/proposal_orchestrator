"""E0 — evidence protocol scaffold for the AWS redeployment.

Acceptance, from ``plans/aws_redeployment_tickets.md`` E0:

1. The new evidence tree exists. No file in the v1 tree changed.
2. The templates match the §7a fields: numbered steps with commands in both
   PowerShell and CloudShell forms, evidence file names, and a PASS criterion
   per file.
3. A test plants each of the four forbidden patterns in a fixture folder, and
   the scan refuses each one. A clean folder passes.
4. Register v2 lists all 41 controls, carries no old-account id, and links
   register v1 as history.

Criterion 1's "no v1 file changed" is a repository fact, checked with git in
the ticket's verification report; these tests check that the new tree sits
beside the old one, not inside it.

The planted values are assembled at run time so that this file itself never
holds a string that looks like a real credential.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools import evidence_secret_scan as scan

INFRA = Path("docs") / "infrastructure_security"
EVIDENCE_V1 = INFRA / "evidence"
EVIDENCE_V2 = INFRA / "evidence_v2"
TEMPLATES = EVIDENCE_V2 / "_templates"
REGISTER_V1 = INFRA / "aws_hardening_control_register.md"
REGISTER_V2 = INFRA / "aws_hardening_control_register_v2.md"

OLD_ACCOUNT_ID = "".join(["2325", "3855", "1827"])
EXPECTED_CONTROLS = {f"DC-{n:02d}" for n in range(1, 41)} | {"PL-8"}

# One planted line per forbidden pattern, in the shape an operator might paste.
PLANTED = {
    "AKIA": '"AccessKeyId": "' + "AK" + "IA" + "TESTFIXTURE0000" + '"',
    "aws_secret": "aws" + "_secret" + "_access_key = <redacted>",
    "SecretString": '"Secret' + 'String": "<redacted>"',
    "SessionToken": '"Session' + 'Token": "<redacted>"',
}


def _clean_folder(root: Path) -> Path:
    folder = root / "R4"
    folder.mkdir()
    (folder / "R4_01_route-table.json").write_text(
        '{"RouteTables": [{"Routes": [{"GatewayId": "local"}]}]}\n', encoding="utf-8"
    )
    (folder / "RUNLOG.md").write_text("| 01 | 10:00 | operator | ok | none | none |\n", encoding="utf-8")
    return folder


# --- criterion 3: the secret scan ------------------------------------------


@pytest.mark.parametrize("pattern", sorted(PLANTED))
def test_scan_refuses_each_forbidden_pattern(tmp_path: Path, pattern: str) -> None:
    folder = _clean_folder(tmp_path)
    (folder / "R4_02_planted.txt").write_text(f"first line\n{PLANTED[pattern]}\n", encoding="utf-8")

    findings = scan.scan_folder(folder)

    assert [(f.path.name, f.line, f.pattern) for f in findings] == [("R4_02_planted.txt", 2, pattern)]
    assert scan.main([str(folder)]) == 1


def test_scan_covers_exactly_the_four_protocol_patterns() -> None:
    assert set(scan.FORBIDDEN_PATTERNS) == set(PLANTED)


def test_clean_folder_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = _clean_folder(tmp_path)

    assert scan.scan_folder(folder) == []
    assert scan.main([str(folder)]) == 0
    assert "CLEAN" in capsys.readouterr().out


def test_scan_reads_nested_files_of_any_extension(tmp_path: Path) -> None:
    folder = _clean_folder(tmp_path)
    nested = folder / "host" / "deeper"
    nested.mkdir(parents=True)
    (nested / "export.png").write_bytes(b"\x89PNG\r\n" + PLANTED["SessionToken"].encode() + b"\x00")

    assert [f.pattern for f in scan.scan_folder(folder)] == ["SessionToken"]


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-be"])
def test_scan_decodes_utf16_files_as_powershell_writes_them(tmp_path: Path, encoding: str) -> None:
    """Windows PowerShell 5.1 redirects with ``>`` in UTF-16; the scan must still see the pattern."""
    folder = _clean_folder(tmp_path)
    data = PLANTED["AKIA"].encode(encoding)
    if encoding == "utf-16-be":
        data = b"\xfe\xff" + data
    (folder / "R1_08_workstation-identity.json").write_bytes(data)

    assert [f.pattern for f in scan.scan_folder(folder)] == ["AKIA"]


def test_case_insensitive_patterns_catch_upper_and_lower_case(tmp_path: Path) -> None:
    folder = _clean_folder(tmp_path)
    (folder / "env.txt").write_text(
        "AWS" + "_SECRET_ACCESS_KEY=<redacted>\nsession" + "token=<redacted>\n", encoding="utf-8"
    )

    assert [f.pattern for f in scan.scan_folder(folder)] == ["aws_secret", "SessionToken"]


def test_access_key_prefix_is_case_sensitive(tmp_path: Path) -> None:
    """Ordinary words such as a country name in a data-flow note are not refused."""
    folder = _clean_folder(tmp_path)
    (folder / "notes.txt").write_text("Partner institutions in Slovakia and Austria.\n", encoding="utf-8")

    assert scan.scan_folder(folder) == []


def test_refusal_reports_location_but_never_the_matching_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = _clean_folder(tmp_path)
    leaked = "TESTFIXTURE0000"
    (folder / "R4_03_leak.json").write_text(PLANTED["AKIA"] + "\n", encoding="utf-8")

    assert scan.main([str(folder)]) == 1
    out = capsys.readouterr().out
    assert "R4_03_leak.json:1: forbidden pattern AKIA" in out
    assert "REFUSED" in out
    assert leaked not in out


def test_missing_folder_is_an_error_not_a_clean_pass(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        scan.scan_folder(tmp_path / "R99")
    assert scan.main([str(tmp_path / "R99")]) == 2


# --- criterion 1: the new tree beside the old one ---------------------------


def test_evidence_v2_tree_exists_beside_v1(repo_root: Path) -> None:
    v1 = (repo_root / EVIDENCE_V1).resolve()
    v2 = (repo_root / EVIDENCE_V2).resolve()

    assert v1.is_dir()
    assert v2.is_dir()
    assert (v2 / "README.md").is_file()
    assert v1 not in v2.parents and v2 not in v1.parents


def test_evidence_v2_tree_is_itself_clean(repo_root: Path) -> None:
    """The templates are copied into every ticket folder, so they must never trip the scan."""
    assert scan.scan_folder(repo_root / EVIDENCE_V2) == []


# --- criterion 2: the templates carry the §7a fields ------------------------


def test_steps_template_has_section_7a_fields(repo_root: Path) -> None:
    text = (repo_root / TEMPLATES / "STEPS.md").read_text(encoding="utf-8")

    assert "### Step 01" in text, "steps are numbered"
    assert "PowerShell:" in text and "```powershell" in text
    assert "CloudShell:" in text and "```bash" in text
    assert "Console path" in text
    assert "| Evidence file | PASS criterion |" in text
    assert re.search(r"<ticket-id>_01_<short-name>\.json", text), "evidence file naming"
    assert "<ticket-id>_outputs.json" in text, "IDs come from saved outputs"


def test_runlog_template_has_section_7a_fields(repo_root: Path) -> None:
    text = (repo_root / TEMPLATES / "RUNLOG.md").read_text(encoding="utf-8")

    assert "(UTC)" in text
    for column in ("Run by", "Deviation from the step sheet", "Error, and what was done about it"):
        assert column in text


def test_verification_template_has_section_7a_fields(repo_root: Path) -> None:
    text = (repo_root / TEMPLATES / "VERIFICATION.md").read_text(encoding="utf-8")

    assert "tools.evidence_secret_scan" in text
    assert "| Step | Criterion | Evidence file | Status | Reason |" in text
    for status in ("PASS", "FAIL", "MISSING", "N/A"):
        assert status in text
    for condition in ("Register v2 updated", "Worklog v2 entry", "Operator confirmed in session"):
        assert condition in text


# --- criterion 4: register v2 -----------------------------------------------


def _register_rows(path: Path) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 2 and re.fullmatch(r"DC-\d{2}|PL-8", cells[1]):
            assert cells[1] not in rows, f"{cells[1]} listed twice in {path.name}"
            rows[cells[1]] = cells[1:-1]
    return rows


def test_register_v2_lists_all_41_controls_as_not_started(repo_root: Path) -> None:
    rows = _register_rows(repo_root / REGISTER_V2)

    assert set(rows) == EXPECTED_CONTROLS
    assert set(rows) == set(_register_rows(repo_root / REGISTER_V1)), "same controls as v1"
    for control, cells in rows.items():
        # Control ID | Name | Requirement | Ticket | Status | Evidence (v2) | Notes
        assert len(cells) == 7, control
        assert cells[4] == "NOT_STARTED", control
        assert cells[5] == "—", control


def test_register_v2_has_an_evidence_path_column(repo_root: Path) -> None:
    text = (repo_root / REGISTER_V2).read_text(encoding="utf-8")
    header = "| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |"

    assert text.count(header) == 10, "one per control group"


def test_register_v2_carries_no_old_id(repo_root: Path) -> None:
    text = (repo_root / REGISTER_V2).read_text(encoding="utf-8")

    assert OLD_ACCOUNT_ID not in text
    assert not re.search(r"\b(?:vpc|vpce|sg|subnet|rtb|fl|i)-[0-9a-f]{8,}\b", text)


def test_register_v2_links_v1_as_history(repo_root: Path) -> None:
    text = (repo_root / REGISTER_V2).read_text(encoding="utf-8")

    assert "](aws_hardening_control_register.md)" in text
    assert "History" in text
