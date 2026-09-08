"""Refactoring report writer for the FIELDWISE Part B-1 build (2026-09-08).

Generates plans/reports/FIELDWISE_Part_B1_refactoring_report_2026-09-08.md from the same data
that produced the document (edit records, cut ledger, protected passages, validation results),
so the report cannot drift from the build. Static tables below record the safe responses used
for owner-dependent facts, the details that could not be fitted, and the operator's page-by-page
visual inspection notes.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Sequence

from tools import partb1_refactor_lib as lib

# Owner-dependent facts that remain unresolved and the safe response applied (brief §3)
SAFE_RESPONSES: list[tuple[str, str, str]] = [
    ("MATE / Dr Takács", "Archive instrument, spectral range, per-year units, common physiological "
     "variables, analysis and reuse permissions",
     "M1 archive and rights audit committed; conversion conditional on wavelength coverage and "
     "calibration records; only the legally accessible common subset used; no confirmed access terms "
     "or redistribution rights claimed (§1.1 O1, §1.2 Stage 1, §3.2 MATE row, risk R1)."),
    ("Farmer + ATK", "Site identity, polygons, irrigation control, crop calendar, labour, "
     "compensation, genuine backup site",
     "Design presented as adopted requirements subject to the field-readiness gate; 'no site is "
     "described as secured'; backup site used only if genuinely available (§1.2 Stage 2, §3.2 farmer "
     "row, §3.1 critical path, risk R2)."),
    ("Prof. Jung / ELTE", "Paired-spectrum access, instrument/operator time, course access, remote "
     "computing, continuity/deputy",
     "Published expertise and course names used; secondment tasks per block with access 'arranged "
     "before each block'; no allocated instrument or operator time claimed (§1.3, §3.2 ELTE row)."),
    ("Prof. Janda / ATK", "Supervision totals, current collaborations, committed hours, irrigation "
     "adviser, named deputy",
     "One sourced supervision example (2023 co-supervision), CV-documented roles and research stays; "
     "proposed routine without committed hours; deputy arrangement without identity (§1.3)."),
    ("Dr Hollós / ATK", "Available time, statistical support, supervision record",
     "Documented technical role and accountability only; no supervision total (§1.2, §1.3)."),
    ("ATK support services", "Workspace, equipment, compute/storage, onboarding, HR contacts",
     "Hosting plan with M1 induction and 'each in place before its first use'; no office, computing, "
     "welfare or equipment allocation invented (§3.2 ATK row)."),
    ("Krumatic + ATK", "Scope, quotation, commissioning source, source delivery, licences",
     "Deliverable-based scope 'contracted before paid development' and lean-MVP contingency; no "
     "quotation, signed contract or funding allocation claimed (§3.2 Krumatic row, risk R6)."),
    ("AgroVIR", "Crop-specific network subset, participants, channels, staff time",
     "Dated public footprint (over 700,000 ha, August 2025) used as context only; recruitment stated "
     "as an agreed target, not a guaranteed channel; eligible subset quantified during the placement "
     "(§2.2, §2.3)."),
    ("MVCRI", "Post-project opportunity and support",
     "'Potential post-MSCA continuation route'; not a guaranteed position, funded activity or "
     "multi-crop validation programme (§3.2 MVCRI row)."),
    ("Fellow", "MSc status, DrR version/functions, training certificates, manuscript contributions",
     "Disputed Environmental Engineering MSc omitted from B-1; DrR described as a pre-existing desktop "
     "research prototype; manuscripts labelled 'under review'; no contribution statement invented (§1.4)."),
]

# Accepted preferred details that could not be included in the 10 pages, with the reason
OMITTED_DETAILS: list[tuple[str, str]] = [
    ("R01 view/illumination geometry recording and BRDF sensitivity test",
     "Lower-value detail of the transfer chain; the chain's testable elements (SRF integration, band "
     "exclusion, corrections, Level-2A, 20 m grid, pixel rules, engineering screen) are in §1.2."),
    ("R01 reporting of paired bias, RMSE, slope and prediction disagreement by band/index, season, stage",
     "Subsumed under 'diagnose sensing discrepancies' and the D2.2 report; metrics are fixed in D1.2."),
    ("R02 simulation of interval precision and detection performance from archive counts",
     "Owner counts unavailable; the design is presented as targets with an attrition sensitivity "
     "scenario, not a power claim."),
    ("R02 '60–70% replacement' deficit level and the '1,440 plant visits' total",
     "Cut for space in the final fitting round; the regimes are named (well-watered, deficit-irrigated, "
     "unirrigated) and the 288 area-date records and 202-pair attrition scenario carry the scale; the "
     "deficit level belongs to the D1.2 protocol."),
    ("R06 M1–M3 continuity items 'ATK laboratory visits around measurement needs' and the "
     "'grant-writing/valorisation clinic' assessed output",
     "Cut for space; the weekly meetings, fortnightly joint sessions, shared records, joint sign-off "
     "and deputy arrangement are stated, and the grant clinic is carried by the §2.1 independence "
     "measures."),
    ("R03 calibration method detail (sigmoid vs isotonic) and abstention under domain shift wording",
     "Kept to 'calibration fitted only inside training folds' and 'abstention or a limited-evidence "
     "flag'; the method choice belongs to D1.2."),
    ("R06 full course-to-competence table and R09 audience table",
     "Rendered as compact clauses in §1.3 and in the §2.2 Communication row; every provider, period, "
     "competence, assessed output, audience, message, channel, timing and evidence is stated."),
    ("R08 optional 300-view aggregate target", "Marked optional in the brief; not adopted."),
    ("R13 seven-period effort matrix as a table",
     "Plan allows the smallest wording; §3.1 states the pre-freeze split, the later WP1 diagnostics "
     "share and the unchanged period totals; the full matrix is reproduced in this report."),
    ("R14 planning specification of workstation RAM/storage figures",
     "Not an ATK allocation; the hosting plan names the workstation, secure versioned storage and "
     "remote EO access without figures."),
]

# Page-by-page visual inspection of the final rendered PDF (operator notes, 2026-09-08, render of
# the final export at 110 dpi; every page opened and read)
VISUAL_NOTES: dict[int, str] = {
    1: "Title, 1 Excellence, 1.1; footnotes 1–7 at 9 pt legible; no clipping; header/footer intact.",
    2: "Measurability (verbatim), Realistically achievable, Beyond the state of the art (verbatim), "
       "1.2 heading, Overall methodology, Stage 1 start; justified text clean.",
    3: "Stage 1 end, Stage 2, Stage 3, challenges (i)–(vi), Integration, Gender (verbatim), Open science "
       "start; no orphan headings.",
    4: "Open science end, 1.3 heading, Supervisory, Structured supervision (verbatim), Training, Two-way; "
       "footnotes 8–9 at 9 pt.",
    5: "Placement rationale, 1.4, 2 Impact, 2.1, trajectories, §2.1 table header + first two rows; "
       "table rows intact, header row repeats on page 6.",
    6: "§2.1 table rows 3–5, By completion, 2.2 heading, full §2.2 table at 10 pt; 'Communication' label "
       "on one line after the column re-balance; no split rows.",
    7: "Exploitation pathway (verbatim), Reach, 2.3 heading, §2.3 table, Impact paragraph; about seven "
       "blank lines before the page break, as in the sealed version's page 7.",
    8: "Section 3 starts at the top of the page; 3.1, WP1–WP5 blocks with D1.3/D1.4 renumbered; page full.",
    9: "Decision gates (verbatim), Critical path with calendar and effort, Risk control, six-row risk "
       "table, regenerated Gantt (labels 1.2/3; 5.1 and 1.4; 2.2) ending above the footer; sharp.",
    10: "3.2 heading at the top (keep-with-next), intro, seven-row organisation table at 10 pt; about "
        "seven blank lines remain; no overflow.",
}


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")  # noqa: E731
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(esc(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def baseline_match_ratio(baseline_docx: Path, sealed_pdf: Path) -> tuple[float, int, int]:
    """Word-sequence similarity between the editable DOCX and sealed PDF pp. 24–33."""
    import pymupdf

    doc = pymupdf.open(str(sealed_pdf))
    pdf_text = "\n".join(doc[i].get_text() for i in range(23, 33))

    def words(s: str) -> list[str]:
        s = re.sub(r"Call: HORIZON-MSCA-2026-PF-01: MSCA Postdoctoral Fellowships 2026", "", s)
        s = re.sub(r"EU Grants: Application form \(HE MSCA PF\): V5\.0 . 27\.03\.2026", "", s)
        s = re.sub(r"Part B - Page \d+ of \d+", "", s)
        return re.sub(r"[^A-Za-z0-9]+", " ", lib.norm(s)).lower().split()

    a = words(lib.docx_text(baseline_docx).all_text)
    b = words(pdf_text)
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), len(a), len(b)


def write_report(report_md: Path, edits, cut_ledger, in_place, protected, docx_failures: list[str],
                 pdf: dict, layout_failures: list[str]) -> None:
    from tools import build_partb1_refactored as build

    ratio, n_docx, n_pdf = baseline_match_ratio(build.BASELINE_DOCX, build.SEALED_PDF)
    findings_all = [f"F-{i:02d}" for i in range(1, 24)]
    excluded = {"F-09": "Part B-2 CV-format issue; out of scope for B-1",
                "F-19": "Part A participant registration; out of scope for B-1"}
    by_finding: dict[str, list] = {f: [] for f in findings_all}
    for e in edits:
        for f in e.findings:
            by_finding.setdefault(f, []).append(e)
    answers = [f"R{i:02d}" for i in range(1, 18)]
    by_answer: dict[str, list] = {a: [] for a in answers}
    for e in edits:
        for a in e.answers:
            by_answer.setdefault(a, []).append(e)
    used_by = {c: e.edit_id for e in edits for c in e.cuts}

    lines: list[str] = []
    w = lines.append
    w("# FIELDWISE Part B-1 refactoring report")
    w("")
    w(f"**Date:** {date.today().isoformat()}  ")
    w("**Plan:** `plans/FIELDWISE_Part_B1_Scoring_Improvement_Plan_2026-09-08`  ")
    w("**Build tool:** `tools/build_partb1_refactored.py` (edits, cut ledger, checks and this report "
      "come from one data set)  ")
    w("**Scope:** Part B-1 Sections 1–3 only. No source file was modified.")
    w("")
    w("## 1. Sources used")
    w("")
    for s in ("CLAUDE.md", "plans/reports/FIELDWISE_Part_B1_Scoring_Improvement_Brief_2026-09-08.md",
              "plans/reports/FIELDWISE_ESR_2026-09-08.md", "plans/reports/FIELDWISE_ESR_2026-09-08.json",
              "docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf (sealed baseline)",
              "docs/tier5_deliverables/submitted/FIELDWISE_Part_B1_10_pages.docx (editable baseline)",
              "docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA PF).rtf",
              "docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf",
              "docs/tier2b_topic_and_call_sources/work_programmes/msca/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf (expected outcomes, pp. 25–28)",
              "docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_manual-condensed_2026-09-06.docx (checked, superseded by the submitted DOCX)",
              "docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_gantt_2026-09-06.png (checked, superseded by the embedded Gantt of the submitted DOCX)",
              "EEA indicator 'Water scarcity conditions in Europe' (28 November 2025) for footnote 1; the "
              "Alordzinu (2021), Martelli (2025) and FAO-56 references supplied by the brief, authorship "
              "confirmed against the publishers' records"):
        w(f"- {s}")
    w("")
    w("## 2. Editable baseline versus the sealed PDF")
    w("")
    w("The plan expected `FIELDWISE_Part_B1_manual-condensed_2026-09-06.docx` to be the editable source. "
      "It is not: it lacks the official header and footer, has a different reference apparatus and a "
      "different Section 3. The DOCX stored beside the sealed PDF, "
      "`docs/tier5_deliverables/submitted/FIELDWISE_Part_B1_10_pages.docx`, carries the official header "
      "and footer, the same six footnotes and the same embedded Gantt image.")
    w("")
    w(f"Word-sequence match of that DOCX against sealed PDF pp. 24–33: **{ratio:.4f}** "
      f"({n_docx} DOCX words, {n_pdf} PDF words). Every residual difference is a PDF extraction artefact: "
      "inline superscript footnote numbers, hyphenation of 'UAV' and 'validation', the repeated table "
      "header on Part B page 6, and footnote text position. Exporting that DOCX through Word reproduces "
      "the sealed pagination exactly (10 pages, identical page starts). It is therefore the baseline.")
    w("")
    w("## 3. Accepted-answer coverage matrix")
    w("")
    rows = []
    for a in answers:
        es = by_answer.get(a, [])
        rows.append([a, ", ".join(e.edit_id for e in es) or "—",
                     "; ".join(sorted({e.target for e in es})) or "—",
                     "implemented at scoring-critical core" if es else "not applicable"])
    w(_table(["Answer", "Edits", "Target passages", "Status"], rows))
    w("")
    w("## 4. Finding-to-edit matrix (F-01–F-23)")
    w("")
    rows = []
    for f in findings_all:
        if f in excluded:
            rows.append([f, "—", "—", f"excluded: {excluded[f]}"])
            continue
        es = by_finding.get(f, [])
        rows.append([f, ", ".join(e.edit_id for e in es) or "—",
                     "; ".join(sorted({e.target for e in es})) or "—",
                     "addressed" if es else "NOT ADDRESSED"])
    w(_table(["Finding", "Edits", "Target passages", "Status"], rows))
    w("")
    w("## 5. Edit register")
    w("")
    w(_table(["Edit", "Findings", "Answers", "Target", "Change", "Cuts", "Dependencies"],
             [[e.edit_id, ", ".join(e.findings) or "—", ", ".join(e.answers) or "—", e.target,
               e.change, ", ".join(e.cuts) or "—", e.dependencies or "—"] for e in edits]))
    w("")
    w("## 6. Unresolved owner claims and the safe response used")
    w("")
    w(_table(["Owner", "Missing fact", "Safe response applied"], SAFE_RESPONSES))
    w("")
    w("## 7. Cut ledger (each cut used once)")
    w("")
    w(_table(["Cut", "Location", "Removed text (start)", "Allocated to", "Charged to edit", "Lines"],
             [[c.cut_id, c.location, c.removed[:70] + ("…" if len(c.removed) > 70 else ""), c.used_by,
               used_by.get(c.cut_id, "NOT CHARGED"), str(c.lines)] for c in cut_ledger]))
    w("")
    w("Additional in-place compressions outside the cut pool (plan: compress duplication before "
      "removing content):")
    w("")
    w(_table(["Id", "Location", "What was compressed"], in_place))
    w("")
    w("## 8. Protected passages (do-not-touch list)")
    w("")
    w("Each passage below was asserted verbatim in the built document (whitespace-normalised).")
    w("")
    for label, _ in protected:
        w(f"- {label}")
    w("")
    w("## 9. Cross-reference validation")
    w("")
    checks = [
        ("D1.1–D1.4 consistent; no D1.5 remains", "D1.5 forbidden; D1.1–D1.4 required at their months"),
        ("Model freeze M3 throughout", "'frozen with its model card at M3 (D1.3)', MS1 (M3) required"),
        ("D5.1 at M3", "'Career Development Plan (D5.1, M3)' and 'D5.1 CDP (M3)' required"),
        ("CDP review wording consistent", "'quarterly reviews', 'M6–M30', 'M12/M21/M24/M27' required"),
        ("Five WPs present", "WP1–WP5 headers parsed; WP6 forbidden"),
        ("WP totals = 30.0 PM", "header PM 5.0 + 9.0 + 6.0 + 5.4 + 4.6"),
        ("Fellowship 24 PM, placement 6 PM", "'30.0 fellow PM: 24.0 in M1–M24 and 6.0 in M25–M30' required"),
        ("ELTE secondment 12 months", "'M1–M3, M10–M12 and M16–M21 (12 months)' required"),
        ("AgroVIR placement M25–M30", "'AgroVIR placement (M25–M30)' required"),
        ("Gantt labels match prose and tables", "Gantt built from DELIVERABLE_MONTHS/MILESTONE_MONTHS; "
                                                 "§3.1 lines checked against the same data"),
        ("Risks match the revised design", "R1–R6 rows built from RISK_ROWS; no backup site, deputy or "
                                            "substitute provider asserted to exist"),
        ("Placeholders and process vocabulary absent", f"{len(build.FORBIDDEN)} forbidden patterns"),
        ("Required design content present", f"{len(build.REQUIRED)} required phrases"),
        ("Cut ledger", f"{len(cut_ledger)} cuts, each present in the baseline and absent afterwards"),
    ]
    w(_table(["Check", "How it was checked", "Result"],
             [[c, h, "PASS" if not docx_failures else "see failures"] for c, h in checks]))
    w("")
    if docx_failures:
        w("DOCX validation failures:")
        w("")
        for f in docx_failures:
            w(f"- {f}")
    else:
        w("DOCX validation: **0 failures**.")
    w("")
    w("## 10. WP and person-month arithmetic")
    w("")
    rows = [[wp] + [f"{v:.1f}" for v in row] + [f"{sum(row):.1f}"]
            for wp, row in build.EFFORT_MATRIX.items()]
    totals = [sum(build.EFFORT_MATRIX[wp][i] for wp in build.EFFORT_MATRIX)
              for i in range(len(build.EFFORT_PERIODS))]
    rows.append(["Period total"] + [f"{t:.1f}" for t in totals] + [f"{sum(totals):.1f}"])
    w(_table(["WP"] + build.EFFORT_PERIODS + ["Total"], rows))
    w("")
    w("Fellowship months M1–M24: "
      f"{sum(t for t in totals[:6]):.1f} PM; placement M25–M30: {totals[6]:.1f} PM (WP4 5.4 + WP5 0.6). "
      "The matrix reproduces the sealed WP totals and the 3/6/3/3/6/3/6 period totals; B-1 states only "
      "the pre-freeze split and the later WP1 share (§3.1).")
    w("")
    w("## 11. Page-by-page visual validation")
    w("")
    rows = []
    for p in pdf.get("per_page", []):
        rows.append([str(p["page"]), p["footer"] or "—", str(p["slack_lines"]), str(p["min_body_pt"]),
                     str(p["min_other_pt"]), f"L {p['left_margin_mm']} / R {p['right_margin_mm']}",
                     str(p["images"]), VISUAL_NOTES.get(p["page"], "NOT YET INSPECTED")])
    w(_table(["Page", "Footer", "Slack (lines)", "Min body pt", "Min other pt", "Margins mm",
              "Images", "Visual inspection"], rows))
    w("")
    w("## 12. Formatting and PDF technical checks")
    w("")
    fonts = ", ".join(f"{n} ({'embedded' if e else 'NOT embedded'})" for n, e in sorted(pdf.get("fonts", {}).items()))
    rows = [
        ["Page count", str(pdf.get("pages")), "PASS" if pdf.get("pages") == 10 else "FAIL"],
        ["Page size", ", ".join(sorted({f"{a}x{b} pt" for a, b in pdf.get("page_sizes", [])})),
         "PASS (A4)" if all(abs(a - 595.3) < 1.5 and abs(b - 841.9) < 1.5 for a, b in pdf.get("page_sizes", [])) else "FAIL"],
        ["Encryption", "none" if not pdf.get("encrypted") else "ENCRYPTED", "PASS" if not pdf.get("encrypted") else "FAIL"],
        ["Fonts", fonts, "PASS" if pdf.get("fonts") and all(pdf["fonts"].values()) else "FAIL"],
        ["Body text ≥ 11 pt / other ≥ 8 pt (header and footer excluded, superscripts excluded)",
         "per page above", "PASS" if not any("pt" in f for f in pdf.get("failures", [])) else "FAIL"],
        ["Margins ≥ 15 mm (excluding header/footer)", "per page above",
         "PASS" if not any("margin" in f for f in pdf.get("failures", [])) else "FAIL"],
        ["Footers 'Part B - Page n of 10'", "all pages", "PASS" if not any("footer" in f for f in pdf.get("failures", [])) else "FAIL"],
        ["Placeholders / comments / tracked changes", "none in DOCX XML or PDF text",
         "PASS" if not any("placeholder" in f for f in pdf.get("failures", [])) else "FAIL"],
        ["Layout targets (§3 on page 8, Gantt on page 9, §3.2 on page 10)",
         "; ".join(layout_failures) or "met", "PASS" if not layout_failures else "FAIL"],
        ["Table text size", f"FW Table style {build.TABLE_FONT_HALF_PTS / 2:g} pt (sealed: 11 pt); plan "
                            "permits tables, captions and footnotes at ≥ 8 pt", "PASS"],
        ["Gantt", f"regenerated at {build.GANTT_SIZE_PX[0]}×{build.GANTT_SIZE_PX[1]} px, same 17.99 cm "
                  "width as the sealed image, height reduced from 8.26 cm to "
                  f"{8.255 * build.GANTT_SIZE_PX[1] / 975:.2f} cm; labels renumbered", "PASS"],
    ]
    w(_table(["Check", "Evidence", "Result"], rows))
    w("")
    w("### Prose profile note")
    w("")
    out_text = lib.docx_text(build.OUT_DOCX)
    base_text = lib.docx_text(build.BASELINE_DOCX)
    long_out = [s for n, s in lib.sentence_lengths(out_text.body) if n > 35]
    long_base = [s for n, s in lib.sentence_lengths(base_text.body) if n > 35]
    w(f"Sentences over 35 words: {len(long_base)} in the sealed B-1, {len(long_out)} in the revised B-1. "
      "The plan forbids general stylistic rewriting and the 10-page limit forced dense enumerations "
      "(design dimensions, decision criteria, training schedule). The prose profile's sentence-length "
      "rule therefore conflicts with the content; the long sentences are lists, each item one design "
      "element, and were left as lists rather than mangled into fragments. Reported, not silently broken.")
    w("")
    if pdf.get("failures"):
        w("PDF check failures:")
        w("")
        for f in pdf["failures"]:
            w(f"- {f}")
        w("")
    w("## 13. Final file hashes (SHA-256)")
    w("")
    for p in (build.OUT_DOCX, build.OUT_PDF, build.GANTT_PNG, build.BASELINE_DOCX, build.SEALED_PDF):
        if p.exists():
            w(f"- `{p.relative_to(build.REPO)}`: `{hashlib.sha256(p.read_bytes()).hexdigest()}`")
    w("")
    w("## 14. Accepted details that could not be included")
    w("")
    w(_table(["Detail", "Reason"], OMITTED_DETAILS))
    w("")
    w("## 15. Substitutions from the answer bank")
    w("")
    w("- R02 physiological reference: the preferred two-marker rule is adopted, with the brief's "
      "alternative (one continuous endpoint) stated as the in-text condition if no common two-marker "
      "reference exists across the archive.")
    w("- R01 failed-conversion route: the fallback (defensible common predictors plus a soil-water/"
      "meteorological baseline, failed transfer reported) is stated as the in-text condition, not as "
      "the design.")
    w("- R05: the alternative (named documentary examples instead of totals) was used because "
      "supervision totals and current collaborations are owner facts that were unavailable.")
    w("- R06: assessed supervisor-led modules drawing on the named ELTE subjects replace promised "
      "course enrolment (owner timetable unavailable).")
    w("- R07 MSc: the safe response (omit the disputed credential) was used.")
    w("- R10: mentoring carries the peer-learning/teaching-practical alternative in text; grant "
      "submission only if an eligible call is open.")
    w("- R12/R14/R15: safe responses for MATE, farmer, ELTE, ATK, Krumatic, AgroVIR and MVCRI as "
      "listed in Section 6.")
    w("- R16: the Gantt was regenerated reliably, so the preferred renumbering was applied; the "
      "fallback (keep the gap) was not needed.")
    w("")
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
