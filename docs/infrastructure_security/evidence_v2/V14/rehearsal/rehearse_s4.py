"""Rehearse runbook §4 on the workstation over a non-sensitive eleven-page Part B.

The page shape follows tests/test_msca_dn_original_import_route.py, extended to one page per
sub-section the historical rubrics anchor (1.1-1.4, 2.1-2.4, 3.1, 3.2, 8).
Commands run in the freeze_bundle worktree, writing to a private root outside
every checkout. Usage: py -3.10 rehearse_s4.py <freeze_bundle> <private root> <traces dir>
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pymupdf

FREEZE, ROOT, TRACES = (Path(a).resolve() for a in sys.argv[1:4])
BIN = Path(__file__).resolve().parent
PRIVATE_DIR = "private/msca_dn_original"
DRY_DIR = "v08_dry_import"
WORKSPACE = "workspaces/msca_dn_original"
CONFIG_FILE = "original_configuration.json"
SUB = dict(submission_id="MSCA-DN-2025-FIXTURE-NOT-THE-REAL-NUMBER", call_id="HORIZON-MSCA-2025-DN-01",
           revision_id="as_submitted_v1", source_id_prefix="SRC-DN-ORIG",
           manifest_name="MSCA-DN-2025_part_b_as_submitted.json")


def run(name: str, module: str, *args: str, expect: int = 0) -> None:
    cmd = [sys.executable, str(BIN / "trace_run.py"), str(TRACES / f"{name}.json"), module, *args]
    r = subprocess.run(cmd, cwd=FREEZE, capture_output=True, text=True)
    (TRACES / f"{name}.out").write_text(r.stdout + r.stderr, encoding="utf-8")
    print(f"{name}: exit={r.returncode} (expected {expect})")
    if r.returncode != expect:
        print(r.stdout[-3000:], r.stderr[-3000:])
        sys.exit(1)


ROOT.mkdir(parents=True)
TRACES.mkdir(parents=True, exist_ok=True)
pdf = ROOT / PRIVATE_DIR / "part_b_as_submitted.pdf"
pdf.parent.mkdir(parents=True)
doc = pymupdf.open()


def page():
    return doc.new_page(width=595, height=842)


def line(p, y, t, size=12):
    p.insert_text((72, y), t, fontsize=size)


SECTIONS = [("1.1", "excellence_section", "Research objectives"), ("1.2", "excellence_section", "Research methodology"),
            ("1.3", "excellence_section", "Training programme quality"), ("1.4", "excellence_section", "Supervision quality"),
            ("2.1", "impact_section", "Impact pathway"), ("2.2", "impact_section", "Career perspectives"),
            ("2.3", "impact_section", "Dissemination and communication"), ("2.4", "impact_section", "Magnitude of impact"),
            ("3.1", "implementation_section", "Work plan and resources"), ("3.2", "implementation_section", "Capacity of participants"),
            ("8", "implementation_section", "Participating Organisations")]
for i, (sid, _sec, title) in enumerate(SECTIONS, start=1):
    p = page()
    if sid == "3.1":
        line(p, 72, "3. Quality and Efficiency of the Implementation")
        line(p, 130, "3.1. Work plan and resources"); line(p, 170, "WP Number: 1")
        line(p, 200, "WP title: Training programme"); line(p, 230, "Lead participant: Beneficiary A")
        line(p, 270, "The work plan runs for 48 months.")
        p.draw_line(pymupdf.Point(72, 330), pymupdf.Point(500, 330))
        for n in range(3):
            p.draw_rect(pymupdf.Rect(90 + n * 40, 340 + n * 14, 180 + n * 60, 352 + n * 14),
                        color=(0, 0, 0), fill=(0.3, 0.5, 0.8))
    else:
        line(p, 72, f"{sid}. {title}")
        line(p, 110, "Beneficiary A hosts two doctoral candidates over 36 months.")
        line(p, 140, "Nine beneficiaries host the candidates across four countries.")
    if i == 1:
        line(p, 800, "1 A footnote set below the body size.", size=7)
doc.save(pdf); doc.close()
sha = hashlib.sha256(pdf.read_bytes()).hexdigest()

run("s4_00_describe", "tools.import_external_proposal", "--document", "official_original", "--describe")
run("s4_01_environment", "tools.import_external_proposal", "--environment")
run("s4_02_dry_import", "tools.dry_import_original", "--pdf", str(pdf), "--expect-sha256", sha,
    "--out", str(ROOT / DRY_DIR), "--submission-id", SUB["submission_id"], "--call-id", SUB["call_id"])

acc = ROOT / DRY_DIR / "extraction_fidelity_acceptance.json"
rec = json.loads(acc.read_text(encoding="utf-8-sig"))
for row in rec["items"]:
    present = row["item"] in {"gantt_chart", "table_headers"}
    row["verdict"] = "preserved" if present else "not_applicable"
    row["basis"] = "operator_page_by_page_check" if present else "not_present_in_this_document"
    row["reconciled_by"] = "the operator"
    row["reconciled_on"] = "2026-11-12"
rec["complete"] = True
acc.write_text(json.dumps(rec, indent=2), encoding="utf-8")
run("s4_03_check_acceptance", "tools.dry_import_original", "--check-acceptance", str(acc))

inv = ROOT / DRY_DIR / "dry_import_inventory.json"
if not inv.exists():
    (inv,) = [p for p in (ROOT / DRY_DIR).glob("*inventory*.json")]
cfg = {
    "schema": None, "record_type": None,
    "config_id": "official_original",
    "declared_by": "the operator, reconciling against the PDF", "declared_on": "2026-11-12",
    "declared_status": "Assumed", "status_note": "Rehearsal over a non-sensitive fixture.",
    "authenticated_sha256": sha,
    "measurement": {"path": f"{DRY_DIR}/{inv.name}", "sha256": hashlib.sha256(inv.read_bytes()).hexdigest()},
    "dry_import_dir": DRY_DIR, "workspace_rel": WORKSPACE,
    "declarations_dir_rel": f"{PRIVATE_DIR}/declarations", "scorecard_rel": None,
    "expected_pages": len(SECTIONS), "body_point_size": "12.0", "marker_page_tolerance": 0,
    "sub_sections": [
        {"sub_section_id": sid, "section_id": sec, "declared_pages": [pg, pg], "marker": f"{sid}.",
         "declared_title": None, "exact_marker": False}
        for pg, (sid, sec, _t) in enumerate(SECTIONS, start=1)],
    "criterion_heading_markers": [{"section_id": "implementation_section", "marker": "3.", "page": 9}],
    "work_package_layout": {"sub_section_id": "3.1",
                            "header_labels": ["WP Number:", "WP title:", "Lead participant:"],
                            "register_declared_labels": ["WP Number:", "WP title:"],
                            "consequence": "Rehearsal fixture."},
    "dn_type": {"value": "standard Doctoral Network", "marker": "Training programme", "page": 9},
    "pages_outside_the_map": [],
    "revisions": [{"revision_id": SUB["revision_id"], "pdf_rel": f"{PRIVATE_DIR}/part_b_as_submitted.pdf",
                   "source_id_prefix": SUB["source_id_prefix"], "manifest_name": SUB["manifest_name"],
                   "register_rel": f"{PRIVATE_DIR}/fidelity_register_as_submitted.json",
                   "candidate_role": "Current assessment artifact: the submitted text itself.",
                   "candidate_version": "as submitted, 11 pages",
                   "summary": "Rehearsal import.", "expected_pages": None, "supersedes": None,
                   "change_id": None}],
}
# schema and record type from the committed template, so nothing is hand-typed
tpl = json.loads((FREEZE / "tools/original_configuration_template.json").read_text(encoding="utf-8-sig"))
cfg["schema"], cfg["record_type"] = tpl["schema"], tpl["record_type"]
(ROOT / CONFIG_FILE).write_text(json.dumps(cfg, indent=2), encoding="utf-8")

run("s4_04_author_workspace", "tools.author_original_workspace", "--root", str(ROOT), "--config-input", CONFIG_FILE)
before = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file())
# As the runbook writes it: refused at the tag (V14-F3)
run("s4_05a_import_as_documented", "tools.import_external_proposal", "--document", "official_original",
    "--config-input", str(ROOT / CONFIG_FILE), "--repo-root", str(ROOT), expect=1)
after = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file())
print("files written by the refused import:", sorted(set(after) - set(before)))
# The same code, one module instance
run("s4_05b_import_in_process", "inproc:tools.import_external_proposal", "--document", "official_original",
    "--config-input", str(ROOT / CONFIG_FILE), "--repo-root", str(ROOT))
print("pdf_sha256", sha)
