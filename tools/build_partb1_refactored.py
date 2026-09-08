"""FIELDWISE Part B-1 refactoring build (plan: plans/FIELDWISE_Part_B1_Scoring_Improvement_Plan_2026-09-08).

Surgically revises the sealed, submitted Part B-1 DOCX (the editable source that matches the
sealed PDF pp. 24-33) into a new 10-page document that implements the accepted answers of the
scoring-improvement brief, then exports it to PDF through Word and validates the result.

Inputs (read only, never modified):
  docs/tier5_deliverables/submitted/FIELDWISE_Part_B1_10_pages.docx   editable baseline
  docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf  sealed PDF

Outputs (new files):
  docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.docx
  docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.pdf
  docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_gantt_refactored_2026-09-08.png
  plans/reports/FIELDWISE_Part_B1_refactoring_report_2026-09-08.md

Every content change is declared below as an EDIT record (finding, brief answer, target
passage, authorised cut, dependencies) so that the report's matrices are generated from the same
data that produced the document. Protected passages of the ESR do-not-touch list are asserted
verbatim after the build; the cut ledger is asserted against the baseline (each cut once, text
gone). Nothing in this file is executed by the orchestration runtime; it is an operator tool.

Run: py -3.10 tools/build_partb1_refactored.py [--no-export] [--render-dir DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import partb1_refactor_lib as lib  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
BASELINE_DOCX = REPO / "docs/tier5_deliverables/submitted/FIELDWISE_Part_B1_10_pages.docx"
SEALED_PDF = REPO / "docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf"
EXPORTS = REPO / "docs/tier5_deliverables/final_exports"
OUT_DOCX = EXPORTS / "FIELDWISE_Part_B1_refactored_2026-09-08.docx"
OUT_PDF = EXPORTS / "FIELDWISE_Part_B1_refactored_2026-09-08.pdf"
GANTT_PNG = EXPORTS / "FIELDWISE_Part_B1_gantt_refactored_2026-09-08.png"
REPORT_MD = REPO / "plans/reports/FIELDWISE_Part_B1_refactoring_report_2026-09-08.md"
BRIEF_MD = REPO / "plans/reports/FIELDWISE_Part_B1_Scoring_Improvement_Brief_2026-09-08.md"
ESR_JSON = REPO / "plans/reports/FIELDWISE_ESR_2026-09-08.json"
PLAN = REPO / "plans/FIELDWISE_Part_B1_Scoring_Improvement_Plan_2026-09-08"

# ---------------------------------------------------------------------------
# Design constants shared by text, tables and Gantt (single source of truth)
# ---------------------------------------------------------------------------
DELIVERABLE_MONTHS = {  # renumbered: former D1.4 model/card -> D1.3, former D1.5 -> D1.4
    "D1.1": 2, "D1.2": 3, "D1.3": 3, "D1.4": 21, "D2.1": 20, "D2.2": 21,
    "D3.1": 24, "D3.2": 24, "D4.1": 30, "D4.2": 30, "D5.1": 3, "D5.2": 6, "D5.3": 30,
}
MILESTONE_MONTHS = {"MS1": 3, "MS2": 12, "MS3": 21, "MS4": 24, "MS5": 27, "MS6": 30}
WP_TOTALS = {"WP1": 5.0, "WP2": 9.0, "WP3": 6.0, "WP4": 5.4, "WP5": 4.6}
EFFORT_PERIODS = ["M1–M3", "M4–M9", "M10–M12", "M13–M15", "M16–M21", "M22–M24", "M25–M30"]
EFFORT_MATRIX = {  # accepted fellow-effort allocation (brief R13), PM per period
    "WP1": [2.2, 0.0, 0.6, 0.0, 2.2, 0.0, 0.0],
    "WP2": [0.3, 4.2, 0.3, 0.6, 3.6, 0.0, 0.0],
    "WP3": [0.2, 1.2, 1.4, 1.3, 0.1, 1.8, 0.0],
    "WP4": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 5.4],
    "WP5": [0.3, 0.6, 0.7, 1.1, 0.1, 1.2, 0.6],
}
PERIOD_TOTALS = [3.0, 6.0, 3.0, 3.0, 6.0, 3.0, 6.0]
GANTT = lib.GanttSpec(
    rows=[
        ("WP1 model / synthesis", [(1, 3), (10, 12), (16, 21)], "#1f5474"),
        ("WP2 field validation", [(1, 21)], "#3f7d5c"),
        ("WP3 web MVP", [(1, 24)], "#6a83a6"),
        ("WP4 placement", [(25, 30)], "#6e5b83"),
        ("WP5 cross-cutting", [(1, 30)], "#9e9e9e"),
        ("ELTE secondment", [(1, 3), (10, 12), (16, 21)], "#cfe2dc"),
    ],
    milestones=[(ms[2:], m) for ms, m in MILESTONE_MONTHS.items()],
    deliverables_a=[("1.1", 2), ("5.2", 6), ("2.1", 20), ("3.1/2", 24), ("4.1/2", 30)],
    deliverables_b=[("1.2/3; 5.1", 3), ("1.4; 2.2", 21), ("5.3", 30)],
)

# ---------------------------------------------------------------------------
# Footnotes: 1-6 exist in the baseline; 1 is re-sourced, 7-9 are added (brief R04)
# ---------------------------------------------------------------------------
FOOTNOTE_1_OLD = " https://www.eea.europa.eu"
FOOTNOTE_1_NEW = (" EEA (2025), Water scarcity conditions in Europe, indicator, 28 Nov. 2025, "
                  "www.eea.europa.eu/en/analysis/indicators/use-of-freshwater-resources-in-europe-1")
NEW_FOOTNOTES = {
    7: ("Alordzinu, K.E., Li, J., Lan, Y. et al. (2021), Rapid Estimation of Crop Water Stress Index "
        "on Tomato Growth, Sensors 21, 5142. doi:10.3390/s21155142"),
    8: ("Martelli, A. et al. (2025), Smart irrigation for management of processing tomato: a machine "
        "learning approach, Irrigation Science 43, 1407–1424. doi:10.1007/s00271-024-00993-9"),
    9: ("Allen, R.G. et al. (1998), Crop Evapotranspiration, FAO Irrigation and Drainage Paper 56, "
        "FAO, Rome."),
}


# ---------------------------------------------------------------------------
# Edit records (report matrices are generated from these)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Edit:
    edit_id: str
    findings: tuple[str, ...]  # ESR finding ids addressed
    answers: tuple[str, ...]  # brief answer ids (R01-R17) implemented
    target: str  # passage in the sealed B-1
    change: str  # one-sentence description
    cuts: tuple[str, ...] = ()  # cut-pool ids consumed (each once)
    dependencies: str = ""  # consistency ripple handled


EDITS: list[Edit] = []


def edit(**kwargs) -> None:
    EDITS.append(Edit(**kwargs))


CUT_LEDGER: list[lib.Cut] = [
    lib.Cut("CUT-25", "§1.1 ¶Problem s2 (p. 1)",
            "High-value horticultural irrigation often relies on delayed visual symptoms, isolated "
            "sensor thresholds or retrospective crop-performance records, risking mistimed or "
            "unnecessary irrigation.", "R02 design/reference/phenology", 2),
    lib.Cut("CUT-1", "§1.1 ¶Pertinence s4–s5 (p. 1)",
            "These objectives also advance the fellow from plant physiologist and agronomist toward an "
            "independent Agricultural Data Scientist integrating plant physiology, Earth observation, "
            "IoT-enabled sensing, predictive modelling and decision-support development. Scientific "
            "and career objectives thus reinforce each other and align directly with MSCA Postdoctoral "
            "Fellowships’ interdisciplinary and inter-sectoral profile.", "R07 researcher evidence", 3),
    lib.Cut("CUT-18", "§1.1 ¶Realistically achievable s3 (p. 2)",
            "Previous MATE research established AquaCrop-based full-to-deficit irrigation treatments "
            "and demonstrated the value and limitations of modelling water stress from irrigation and "
            "crop-water-demand information alone.", "R01/R03 transfer chain and named model", 2),
    lib.Cut("CUT-22", "§1.2 ¶Overall methodology s2 (p. 2)",
            "Operational predictors comprise spectral, soil-water and meteorological variables.",
            "R01/R03 transfer chain and named model", 1),
    lib.Cut("CUT-9", "§1.2 ¶Integration of methods s2 (p. 3)",
            "HUN-REN ATK supplies plant-stress physiology/modelling; MATE the multi-season "
            "controlled-irrigation archive and processing-tomato expertise; Prof. András Jung/ELTE "
            "hyperspectral-to-Sentinel harmonisation, EO methodology and sensing-scale transfer through "
            "a distributed 12-month secondment; and Krumatic/AgroVIR software-engineering and "
            "operational farm-management perspectives.", "R01/R03 transfer chain and named model", 1),
    lib.Cut("CUT-19", "§1.2 ¶Methodological challenges, UAV sentences (p. 3)",
            "If clouds or acquisition timing prevent usable Sentinel-2 observations at critical "
            "validation dates, targeted UAV flights may supply supplementary high-resolution "
            "observations, subject to platform availability and flight conditions. These support "
            "interpretation but do not replace Sentinel-2 in the primary transferability assessment.",
            "R02 design/reference/phenology", 2),
    lib.Cut("CUT-23", "§1.3 ¶Planned training s5 (p. 4)",
            "These activities advance the fellow toward an independent Agricultural Data Scientist at "
            "the physiology–EO–predictive decision-support interface.", "R02 design/reference/phenology", 1),
    lib.Cut("CUT-12", "§1.2 ¶Stage 3 condensed to one sentence (p. 3)",
            "DrR – Digital Agronomist enters FIELDWISE as the fellow’s pre-existing, independently "
            "developed research prototype.", "R08 magnitude", 1),
    lib.Cut("CUT-11", "§1.3 ¶Rationale and added value s6 (p. 4)",
            "Commercially sensitive evaluation uses protected, coded or appropriately aggregated data.",
            "R08 magnitude", 1),
    lib.Cut("CUT-10", "§1.3 ¶Supervisory architecture s7 (p. 4)",
            "The host also provides demonstrated European-project experience: ATK coordinated the MSCA "
            "Individual Fellowship LANDRACES (752453) and participates in Horizon Europe projects "
            "including COUSIN, AI4SoilHealth and TUdi.", "R05 supervision evidence", 2),
    lib.Cut("CUT-20", "§1.3 ¶Two-way transfer s1 (p. 4)",
            "FIELDWISE connects internationally recognised plant-stress physiology, "
            "predictive-modelling, EO and precision-irrigation expertise.", "R06/R10 training and career", 1),
    lib.Cut("CUT-13", "§2.1 ¶FIELDWISE is designed s2 (p. 5)",
            "The fellowship builds on competences already established in physiology, agronomy, EO and "
            "data analysis and adds the advanced capabilities required for scientific independence: "
            "leakage-safe predictive modelling, uncertainty and calibration, sensing-scale transfer, "
            "operational EO workflows, research-to-software translation and inter-sectoral "
            "exploitation.", "R09 communication", 2),
    lib.Cut("CUT-8", "§2.1 ¶By completion s3 (p. 6)",
            "The 12-month ELTE secondment adds sustained inter-institutional experience and EO "
            "specialisation, while the AgroVIR placement provides direct non-academic experience.",
            "R09 communication", 1),
    lib.Cut("CUT-17", "§2.2 ¶FIELDWISE uses a targeted strategy s2 (p. 6)",
            "Target groups are research communities, growers and advisors, FMIS/agri-software and "
            "technology-transfer actors, students and the wider public.", "R09/R11 reach and release", 2),
    lib.Cut("CUT-7", "§2.3 ¶Impact is measured s3 (p. 7)",
            "Delivery is tracked through K1–K14, covering archive harmonisation and stress-reference "
            "definition, frozen model and transfer specification, prospective validation, web-MVP "
            "readiness and external evaluation, post-MSCA exploitation planning and Career Development "
            "Plan implementation.", "R01/R02 overflow (three-scale magnitude)", 3),
    lib.Cut("CUT-5", "§3.1 ¶D5.1 CDP last sentence (pp. 8–9)",
            "Required administrative outputs: mobility declaration within 20 days of research-training "
            "start, updated as needed; end-of-training questionnaire and follow-up two years later.",
            "R17 risk triggers / R13 effort", 2),
    lib.Cut("CUT-14", "§3.1 ¶The fellow leads s2 (p. 8)",
            "Five WPs connect a frozen historical-data model, two prospective tomato seasons, "
            "evidence-limited software translation and career development.", "R17 risk triggers / R13 effort", 1),
    lib.Cut("CUT-15", "§3.1 ¶Lead: fellow/ATK; supervisors (WP5 verbs) (p. 8)",
            "implement the CDP, quarterly reviews, technical/transferable skills and knowledge exchange.",
            "R13 start window and contingency", 1),
    lib.Cut("CUT-16", "§3.1 ¶D2.1 dataset K5 (p. 8)",
            "all scheduled observation opportunities accounted for, with", "R13 start window and contingency", 1),
    lib.Cut("CUT-2", "§3.2 ATK row s4 (p. 10)",
            "Where available and formally assigned early-stage female researchers will participate in "
            "field measurements under supervision, providing practical research-training opportunities "
            "and supporting gender-balanced participation.", "R14 hosting provision", 2),
    lib.Cut("CUT-3", "§3.2 ELTE row s5 (p. 10)",
            "Where available, female students will participate in EO/geospatial processing and "
            "measurement activities under supervision, strengthening practical training and "
            "gender-balanced participation.", "R14 hosting provision", 2),
    lib.Cut("CUT-4", "§3.2 MVCRI row condensed (p. 10)",
            "The institute provides a realistic pathway for crop-specific recalibration, further "
            "validation in other high-value irrigated vegetable crops, and transfer of FIELDWISE "
            "knowledge to Bulgarian production conditions.", "R12 dependency status", 2),
]

# In-place compressions outside the cut pool (plan: 'compress duplication before removing content')
IN_PLACE_COMPRESSIONS: list[tuple[str, str, str]] = [
    ("IPC-1", "§1.1 ¶Realistically achievable s1 and s4",
     "Duration sentence repeated in §2.3 and §3.1; 'links this imposed deficit context' repeated in "
     "§1.2 Overall methodology."),
    ("IPC-2", "§1.1 ¶Four objectives, O2–O4",
     "Deficit-context, Sentinel-input and partner-role sentences merged; each is stated once in §1.2."),
    ("IPC-3", "§1.2 ¶Stage 1 ELTE secondment sentence",
     "Secondment description kept in §1.3, §2.1 and §3.2; Stage 1 keeps only ELTE's role in the "
     "sensor-transfer specification."),
    ("IPC-4", "§1.2 ¶Integration of methods s1–s2 merged",
     "Discipline list and role assignments merged into one sentence with accountabilities."),
    ("IPC-5", "§1.3 ¶Supervisory architecture s1",
     "Generic opener ('complementary expertise') removed; the evidence sentences carry the content."),
    ("IPC-6", "§1.4 ¶A profile matched",
     "Undated Kleffmann employment, unnamed AI/ML course list, Novi Sad mobility, the disputed MSc "
     "claim and two duplicated fit sentences removed; three competence-to-task links replace them."),
    ("IPC-7", "§3.2 intro s3",
     "'Each participating organisation contributes a complementary capacity' replaced by the "
     "dependency and resource-priority statements."),
    ("IPC-8", "§1.1 ¶Problem s5, ¶Pertinence closer, §2.3 intro s1, §2.3 Scientific row, §2.1 ¶By "
     "completion s2 and closer, §2.1 ¶Two trajectories, §1.2 ¶Integration opener, §1.3 ¶Placement s7",
     "Restated scope, duration, novelty and closing sentences compressed; each fact remains stated "
     "once elsewhere (the placement's IP arrangements are carried by the §2.2 IP row)."),
    ("IPC-9", "§2.1 table training rows",
     "The 'ATK scientific and modelling training' and '12-month distributed ELTE secondment' rows "
     "merged into one row; both measures and their evidence retained."),
]

# Protected passages (ESR do-not-touch list) that must survive verbatim
PROTECTED: list[tuple[str, str]] = [
    ("§1.1 Beyond the state of the art (four assumptions, three advances)",
     "FIELDWISE challenges four assumptions: vegetation indices themselves represent water stress; "
     "proximal and satellite observations are interchangeable; internal validation demonstrates field "
     "transferability; and one crop’s model transfers unchanged to another. Its ambition is a "
     "physiologically validated, uncertainty-aware transfer framework, not a new machine-learning "
     "algorithm, testing whether relationships learned from controlled experiments remain valid across "
     "unseen years, sensing scales and commercial fields. Three citable advances are: (1) a "
     "probabilistic processing-tomato water-stress model documenting calibration, uncertainty and "
     "blocked unseen-year performance; (2) a prospective experimental-to-commercial-field transfer gap "
     "quantified with a model frozen before deployment; and (3) a specification separating reusable "
     "modelling components from sensing-scale and crop-specific elements requiring recalibration. The "
     "new knowledge quantifies whether, how far and under what conditions predictive validity survives "
     "transfer from controlled experiments to operational satellite-based monitoring."),
    ("§1.1 Measurability and verifiability (metrics, M3 freeze, falsifiable hypothesis)",
     "development within the historical archive will use blocked, leakage-safe unseen-year validation. "
     "The stress-reference definition, predictors, feature-selection rules, evaluation metrics and "
     "permitted recalibration strategy will be pre-specified in D1.2. The frozen model will "
     "subsequently be tested prospectively over two unseen commercial-field seasons. Performance will "
     "be evaluated using balanced accuracy, F1 and ROC-AUC for stress detection; reliability and Brier "
     "score for probabilistic calibration; and lead time and false-alarm rate for operational value. "
     "Regression metrics will be used only if the archive supports a defensible continuous "
     "stress-severity reference. Freezing the model and predictor definitions at M3 prevents "
     "retrospective optimisation against prospective outcomes and makes the central hypothesis directly "
     "falsifiable: whether water-stress relationships learned from controlled experimental observations "
     "remain valid when corresponding predictors are obtained from actual Sentinel-2 observations under "
     "commercial-field conditions."),
    ("§1.2 Stage 2 s1 and s4–s6 (frozen model, primary before recalibration)",
     "The frozen model uses actual Sentinel-2 indices, soil-water and meteorological observations; "
     "coordinated physiology independently verifies realised plant stress. Primary performance precedes "
     "any recalibration; subsequent limited recalibration is secondary and pre-specified. The transfer "
     "gap quantifies predictive validity retained from controlled experiments to genuine satellite-scale "
     "field monitoring (D2.1–D2.2, M20–M21). Crop transfer is addressed separately, distinguishing "
     "reusable components from those requiring crop-specific recalibration and revalidation."),
    ("§1.2 Methodological challenges (i)–(vi)",
     "(i) A year-by-variable availability matrix and only defensible common predictors manage "
     "inter-annual archive heterogeneity; (ii) pre-model spectral harmonisation and prospective "
     "scale-transfer testing link hyperspectral and satellite observations without assuming "
     "interchangeability; (iii) blocked unseen-year validation avoids optimistic random-split "
     "generalisation; (iv) a model frozen before deployment tests commercial-field transfer, reporting "
     "performance before recalibration; (v) sufficiently large treatment areas and valid interior "
     "observations reduce Sentinel mixed-pixel risk; and (vi) parsimony, uncertainty assessment, lead "
     "time and false-alarm rate control over-fitting."),
    ("§1.2 Gender dimension and other diversity aspects",
     "A sex/gender dimension is not relevant to the biological research content, which concerns "
     "processing-tomato water-stress responses and involves no human or animal biological data. "
     "Diversity becomes relevant only in end-user interaction: usability feedback will consider "
     "differences in farm context and digital literacy. Any grower feedback will follow "
     "informed-consent, withdrawal, data-minimisation and coded/anonymised-processing principles."),
    ("§1.3 Structured supervision and governance",
     "Supervision comprises regular one-to-one meetings with Prof. Janda, dedicated modelling/EO "
     "technical sessions with specialists, monthly written progress monitoring and quarterly Career "
     "Development Plan reviews. The Project Steering Group—fellow, primary supervisor, specialist "
     "co-supervisor/modelling expert and relevant partner contacts—reviews protocol/model freeze, "
     "prospective-field implementation, transfer-validation completion, MVP readiness and the "
     "non-academic placement. Pre-defined decision responsibilities and a two-step conflict-resolution "
     "route ensure continuity while protecting the fellow’s growing scientific independence."),
    ("§1.3 Two-way transfer s2–s4",
     "HUN-REN ATK contributes advanced abiotic-stress physiology, phenotyping and modelling; ELTE "
     "established hyperspectral-sensing, geoinformatics and satellite-EO expertise. The fellow "
     "contributes drought-stress physiology, remotely monitored plant-stress responses, field "
     "physiological phenotyping and interpretation under contrasting water availability, strengthening "
     "stress biology’s translation into irrigation decision support. Joint supervision, the distributed "
     "ELTE secondment, shared MATE-archive analysis, prospective field validation, teaching and "
     "co-authored publications reinforce exchange."),
    ("§1.3 Rationale and added value of the placement s1–s5",
     "The six-month AgroVIR placement (M25–M30) is an integral inter-sectoral component of FIELDWISE, "
     "providing competences not fully available academically: DrR web-MVP operational evaluation, FMIS "
     "requirements engineering, interoperability assessment, user-oriented testing and exploitation "
     "planning. AgroVIR supplies requirements feedback during the fellowship; the placement adds "
     "intensive exposure to production agricultural software and decision-support workflows. Structured "
     "technical reviews assess usability, data-flow requirements, missing-data behaviour, "
     "interoperability and the pathway toward future FMIS integration."),
    ("§2.2 Exploitation row",
     "Maturation of the fellow’s pre-existing DrR desktop prototype into a validated web MVP. FIELDWISE "
     "provides validated scientific/EO functionality; Krumatic provides remunerated software "
     "engineering; AgroVIR provides requirements and operational evaluation. Post-MSCA routes include "
     "FMIS integration, MVCRI crop extension and HUN-REN/HUNRENTECH-supported licensing or "
     "researcher-led start-up/spin-off exploration."),
    ("§2.2 IP and knowledge management row",
     "Separate rights layers for DrR background / FIELDWISE-generated results / institutional datasets "
     "/ contracted code. A dated DrR declaration establishes the pre-action baseline. Ownership/licensing "
     "of the new web software and source code is defined through the relevant HUN-REN ATK–Krumatic "
     "agreement; AgroVIR receives only access required for evaluation."),
    ("§2.2 Exploitation pathway",
     "DrR enters FIELDWISE as the fellow’s pre-existing, independently developed research prototype. "
     "Only scientifically validated functions are transferred into the web MVP. At M24 the result is a "
     "validated MVP, followed by independent AgroVIR evaluation in M25–M30 before any claim of FMIS "
     "readiness or wider commercial deployment. FIELDWISE therefore delivers four exploitable result "
     "families: the validated stress-prediction workflow, the hyperspectral-to-Sentinel transfer "
     "methodology, the matured DrR web MVP, and the AgroVIR-informed FMIS-integration specification."),
    ("§2.3 water-saving boundary",
     "Warning lead time, false alarms, uncertainty and water–yield–quality relationships are measured "
     "prospectively; no numerical water-saving benefit is claimed in advance."),
    ("§3.1 Decision gates and dependencies",
     "MS1 (M3): protocol lock precedes fitting and model freeze; field launch plan/CDP agreed. MS2 "
     "(M12): season 1 QC and logistics review, retaining the primary model. MS3 (M21): two-season "
     "transfer evidence and specification accepted; permitted MVP functions decided. MS4 (M24): "
     "critical tests and placement scope accepted. MS5 (M27): midpoint assessment/corrections agreed. "
     "MS6 (M30): external assessment and roadmaps completed. The fellow and ATK approve scientific "
     "gates with specialist input; AgroVIR co-reviews MS4–MS6."),
    ("§3.1 Risk control integrity rule",
     "Poor transfer is a reportable scientific result; it does not authorise unsupported advice."),
    ("§3.1 K1–K4", "K1–K4: five seasons audited; one locked protocol; reproducible, leakage-safe "
                   "held-out-year results; one reusable/crop-specific transfer specification."),
    ("§3.1 K6", "K6: season-level and pooled discrimination, calibration, false alarms, lead time and "
                "transfer gap, with uncertainty or non-estimability explained."),
    ("§3.1 K7–K8", "K7: one MVP, all agreed critical tests pass and zero unresolved critical defects in "
                   "the released scope. K8: source access, rights, evidence limits, guidance and "
                   "evaluation scope documented."),
    ("§3.1 K9–K10", "K9: all six dimensions assessed and priority issues dispositioned. K10: roadmap "
                    "states owners, IP/access, technical dependencies, actors, resources and decision gates."),
    ("§3.1 K11–K14", "K11: CDP reviews, four technical competence strands and 12 secondment months "
                     "evidenced. K12: all released assets have metadata and access decisions. K13: ≥2 "
                     "manuscripts submitted, ≥2 conference presentations and ≥1 end-user workshop by M30. "
                     "K14: each result family has an owner, audience, route and indicators."),
    ("§3.1 WP headers", "WP1 — Data harmonisation, stress definition & model development | M1–M21 | 5.0 PM."),
    ("§3.1 WP headers", "WP2 — Prospective field validation | M1–M21 | 9.0 PM."),
    ("§3.1 WP headers", "WP3 — DrR web MVP and readiness | M1–M24 | 6.0 PM."),
    ("§3.1 WP headers", "WP4 — AgroVIR placement | M25–M30 | 5.4 PM."),
    ("§3.1 WP headers", "WP5 — Training, open science, dissemination and management | M1–M30 | 4.6 PM."),
]

# Strings the final proposal must not contain (plan: final proposal must not mention ...)
FORBIDDEN: list[tuple[str, str]] = [
    (r"\[OWNER-CONFIRM", "placeholder"), (r"\[TBC\]", "placeholder"), (r"\bTODO\b", "placeholder"),
    (r"\bTBD\b", "placeholder"), (r"\?\?", "placeholder"), (r"\[\?\]", "placeholder"),
    (r"\bESR\b", "evaluation-report mention"), (r"scoring[- ]improvement", "brief mention"),
    (r"preferred answer", "brief vocabulary"), (r"owner fact", "brief vocabulary"),
    (r"unavailable fact", "brief vocabulary"), (r"\bfallback\b", "drafting alternative vocabulary"),
    (r"refactor", "process vocabulary"), (r"score estimate", "process vocabulary"),
    (r"simulated evaluator", "process vocabulary"), (r"page[- ]budget", "process vocabulary"),
    (r"cut pool", "process vocabulary"), (r"\bD1\.5\b", "renumbered deliverable"),
    (r"where technically possible", "hedged harmonisation (A-20)"),
    (r"where institutional, commercial and IP rights permit", "conditional sharing (A-22)"),
    (r"is holding Environmental Engineering", "disputed credential (A-02)"),
    (r"Environmental Engineering", "disputed credential omitted (safe response)"),
    (r"Kleffmann", "undated employment removed"), (r"\bWP6\b", "five WPs"),
    (r"secured site|site is secured|is already secured", "no secured-site wording"),
    (r"signed (data|development|placement) agreement", "no signed-agreement wording"),
    (r"water saving[s]? of", "no numerical water-saving claim"),
    (r"pending written confirmation", "orchestration-era flag vocabulary"),
    (r"orchestrat", "no orchestration vocabulary"),
]

REQUIRED: list[tuple[str, str]] = [
    ("frozen with its model card at M3 (D1.3)", "R03 freeze and renumbering"),
    ("D1.4 transfer specification (M21)", "R16 renumbering in §3.1"),
    ("Career Development Plan (D5.1, M3)", "D5.1 stays at M3"),
    ("quarterly reviews", "CDP cadence in §2.1/§3.1"),
    ("M6–M30", "quarterly cadence months"),
    ("M12/M21/M24/M27", "transition reviews"),
    ("M1–M3, M10–M12 and M16–M21 (12 months)", "12 secondment months"),
    ("AgroVIR placement (M25–M30)", "placement timing"),
    ("30.0 fellow PM: 24.0 in M1–M24 and 6.0 in M25–M30", "effort totals"),
    ("no numerical water-saving benefit is claimed in advance", "water-saving boundary"),
    ("700,000", "AgroVIR attributed figure"),
    ("balanced accuracy ≥0.70", "R03 decision criteria"),
    ("sensitivity ≥0.80", "R03 decision criteria"),
    ("false-positive rate ≤0.20", "R03 decision criteria"),
    ("Brier skill", "R03 decision criteria"),
    ("leave-one-year-out", "R03 validation"),
    ("regularised logistic regression", "R03 model"),
    ("gradient-boosted trees", "R03 benchmark"),
    ("spectral-response functions", "R01 chain"),
    ("Level-2A", "R01 chain"),
    ("20 m", "R01 chain"),
    ("≤0.25 historical standard deviations", "R01 engineering screen"),
    ("≤10% change in stress classifications", "R01 engineering screen"),
    ("three irrigation regimes", "R02 design"),
    ("four spatial blocks", "R02 design"),
    ("12 separately managed", "R02 design"),
    ("80 × 80 m", "R02 design"),
    ("40 × 40 m", "R02 design"),
    ("7.68 ha", "R02 design"),
    ("288 area-date records", "R02 design"),
    ("202 area-date pairs", "R02 design"),
    ("stomatal conductance relative to stage- and campaign-matched well-watered controls", "R02 reference"),
    ("indeterminate", "R02 reference"),
    ("Alordzinu", "R04 reference (footnote)"),
    ("Martelli", "R04 reference (footnote)"),
    ("FAO Irrigation and Drainage Paper 56", "R04 reference (footnote)"),
    ("Széchenyi István University", "R05 Janda supervision example"),
    ("Hyperspectral Imaging and Field Spectroscopy", "R06 Jung course"),
    ("weekly Janda–fellow meetings", "R06 supervision routine"),
    ("fortnightly joint physiology/EO/modelling sessions", "R06 supervision routine"),
    ("under review", "R07 manuscripts labelled under review"),
    ("COST PANGEOS Short-Term Scientific Mission at MATE", "R07 evidence"),
    ("pre-existing desktop research prototype", "R07 DrR status"),
    ("6–10 growers", "R08/R09 targets"),
    ("2–3 FMIS", "R08/R09 targets"),
    ("about 20 participants", "R09 workshop target"),
    ("three illustrated explainers", "R09 explainers"),
    ("one reusable tutorial", "R09 tutorial"),
    ("Water Resilience Strategy", "R08 policy link"),
    ("methods clinic by M12", "R10 career measure"),
    ("mock-reviewed application", "R10 career measure"),
    ("mentor", "R10 career measure"),
    ("Zenodo", "R11 repository"),
    ("BSD-3-Clause", "R11 licence"),
    ("preprint", "R11 preprint"),
    ("30-day", "R11 disclosure review"),
    ("February start", "R13 calendar"),
    ("Pre-freeze WP1 effort is 2.2 PM", "R13 effort rationale"),
    ("field-readiness gate", "R12 field readiness"),
    ("legally accessible common subset", "R12 MATE safe response"),
    ("lean MVP", "R12/R15 Krumatic fallback"),
    ("potential post-MSCA continuation route", "R12 MVCRI safe response"),
    ("MVCRI has no core in-action validation role during the project", "protected MVCRI sentence"),
    ("Resources are prioritised in this order", "R15 priority order"),
    ("R6 | WP3–5 | M/M", "R17 engineering/IP/placement risk row"),
    ("R5 | WP1–2 | L/H", "R17 supervisor/ELTE access risk row"),
    ("designated deputy", "R17 supervisor/ELTE risk"),
]

RISK_ROWS = [  # (first cell, second cell) — decision-specific triggers and responses (brief R17)
    ("R1 | WP1 | M/H",
     "Archive rights/coverage insufficient at the M1 audit, or pipeline not reproducible by M3: use "
     "only the legally accessible common subset; freeze the specified baseline; never fit to "
     "prospective outcomes; redesign O1–O2 if the core archive is absent. Owner: fellow/ATK/MATE."),
    ("R2 | WP2 | M/H",
     "Site geometry, irrigation isolation or two-season access unavailable at the field-readiness "
     "decision: activate an identified comparable site only if genuinely available; otherwise rephase "
     "or narrow the evidence claim before planting. Owner: fellow/ATK/producer."),
    ("R3 | WP2 | H/M",
     "Failed calibration, insufficient interior coverage or too few matched dates: spares and manual "
     "reference checks; logged missingness; claims limited to valid coverage; UAV supplementary only. "
     "Owner: fellow/ELTE/producer."),
    ("R4 | WP2–3 | M/H",
     "Poor transfer: report unchanged-model performance first; evaluate recalibration separately; limit "
     "MVP and placement to supported functions; a negative result still fulfils the reporting "
     "objective. Owner: fellow/ATK/AgroVIR."),
    ("R5 | WP1–2 | L/H",
     "Prolonged supervisor absence, or a critical review or ELTE access window missed: a designated "
     "deputy and remote joint review; substitute facility only where genuinely equivalent and "
     "available. Owner: ATK/ELTE."),
    ("R6 | WP3–5 | M/M",
     "Critical tests missed, source rights unresolved or placement withdrawn: scope and rights agreed "
     "before paid development; narrow to the lean MVP; replacement provider only if secured; placement "
     "change resolved with the host. Owner: fellow/ATK; Krumatic/AgroVIR."),
]
TABLE_WIDTHS_CM = {  # re-balanced columns (totals unchanged) so the tallest cells wrap less
    "Measure": [3.2, 10.4, 4.4],
    "Strand": [2.9, 2.4, 9.4, 3.3],  # 2.9 cm keeps bold 'Communication' on one line at 10 pt
    "Dimension": [2.5, 6.1, 9.4],
    "Risk; likelihood/impact": [3.0, 15.0],
    "Organisation": [2.9, 15.09],
}


# ---------------------------------------------------------------------------
# The edits
# ---------------------------------------------------------------------------
def apply_edits(doc) -> None:
    P = lambda anchor: lib.find_paragraph(doc, anchor)  # noqa: E731
    S = lib.set_paragraph_markup

    # ======================= 1.1 =======================
    edit(edit_id="E01", findings=("F-05",), answers=("R04",), target="§1.1 ¶Problem and overarching aim",
         change="Generic problem sentence removed (CUT-25, allocated to E08); footnote 1 re-sourced to "
                "the EEA indicator.",
         dependencies="Footnote 1 text replaced in footnotes.xml.")
    S(P("Problem and overarching aim."),
      "**Problem and overarching aim.** European agriculture faces increasing water constraints: "
      "approximately 30% of EU territory experiences seasonal water scarcity in an average year, while "
      "climate change is expected to intensify drought frequency, severity and seasonal freshwater "
      "fluctuations[^1]. FIELDWISE asks: **can a physiologically grounded plant water-stress signal "
      "remain valid across seasons, environments and sensing scales, survive prospective validation "
      "under real commercial-field conditions, and be translated into crop-configurable irrigation "
      "decision support?** Processing tomato is the **development and validation crop**, supported by "
      "an unusually rich five-season (2022–2026) archive of physiological, soil, meteorological and "
      "proximal-spectral observations. An end-of-project non-academic placement completes "
      "inter-sectoral translation.")

    edit(edit_id="E02", findings=("F-05",), answers=("R04",), target="§1.1 ¶Pertinence",
         change="Position FIELDWISE against thermal/CWSI, soil-water/ET/AquaCrop scheduling and ML tomato "
                "irrigation work with three new footnotes; the FIELDWISE addition stated; career "
                "duplicate cut (CUT-1).", cuts=("CUT-1",),
         dependencies="Footnotes 7–9 added; Word renumbers the displayed footnotes in order.")
    S(P("Pertinence."),
      "**Pertinence.** Three linked scientific gaps motivate the objectives: (i) insufficient "
      "physiological grounding of water-stress indicators; **(ii)** limited evidence of predictive "
      "validity across unseen years, environments and sensing scales; and **(iii)** weak translation "
      "into operational irrigation decision support. Spectral and environmental variables frequently "
      "serve as stress proxies without demonstrated consistency with plant physiological "
      "responses[^2]. Existing tomato approaches already supply thermal/CWSI stress assessment[^7], "
      "soil-water, evapotranspiration and AquaCrop-based scheduling[^9] and machine-learning "
      "irrigation support for processing tomato[^8]; none has been tested as a model frozen before "
      "deployment and carried, with its uncertainty, across years, an independent field and the "
      "proximal-to-satellite scale, which is the evidence FIELDWISE adds.")

    edit(edit_id="E03", findings=("F-01", "F-03", "F-23"), answers=("R01", "R03", "R16"),
         target="§1.1 ¶The four objectives (O1–O4)",
         change="O1 states the conditional spectral conversion; O2 names the model and benchmark and the "
                "renumbered D1.3; O3 names the replicated design; O2–O4 duplicates merged (IPC-2).",
         dependencies="D1.4→D1.3 here, §1.2, §2.1, §2.2, §3.1 and Gantt.")
    S(P("The four objectives, and why they are measurable and verifiable"),
      "**The four objectives, and why they are measurable and verifiable.** **O1 — Harmonise the "
      "2022–2026 MATE archive and establish the water-stress reference and validation protocol.** The "
      "five-season archive of physiological, soil-water, meteorological and hyperspectral observations "
      "under contrasting, AquaCrop-derived irrigation treatments[^3],[^4] is harmonised, and canopy "
      "spectra are converted to synthetic Sentinel-2 predictors only where wavelength coverage and "
      "calibration records support it (Section 1.2). Outputs: harmonised database and "
      "predictor-availability map (**D1.1, M2**); stress-reference, feature-selection and "
      "physiological-validation protocol (**D1.2, M3**). **O2 — Develop an interpretable and "
      "uncertainty-aware probabilistic water-stress model.** A regularised logistic regression on a "
      "pre-specified predictor set, benchmarked against constrained gradient-boosted trees, predicts "
      "water-stress probability and operational stress status from Sentinel-compatible indices, "
      "soil-water and meteorological variables against an independently measured physiological "
      "reference. Output: model, benchmark, predictor definitions and model card frozen at **M3 "
      "(D1.3)**. **O3 — Prospectively validate the frozen model under unseen commercial-field "
      "conditions over two processing-tomato seasons.** A replicated design (three irrigation regimes "
      "in four blocks, Section 1.2) in a commercial field with valid Sentinel-2 treatment areas, with "
      "coordinated physiology verifying the plant response independently. Outputs: prospective "
      "validation dataset (**D2.1, M20**); transferability and uncertainty report (**D2.2, M21**). "
      "**O4 — Translate validated outputs into the DrR web MVP and assess their operational "
      "relevance.** Building on the fellow’s pre-existing desktop DrR prototype, with Krumatic "
      "engineering and AgroVIR requirements, feedback and final non-academic evaluation, only "
      "validated outputs enter the prototype. Outputs: web MVP and readiness dossier (**D3.1–D3.2, "
      "M24**); operational/interoperability assessment and roadmap (**D4.1–D4.2, M30**).")

    edit(edit_id="E04", findings=(), answers=(), target="§1.1 ¶Measurability and verifiability",
         change="Only the missing space after 'verifiability.' is restored (permitted by the do-not-touch list).")
    S(P("Measurability and verifiability"),
      "**Measurability and verifiability.** Model development within the historical archive will use "
      "blocked, leakage-safe unseen-year validation. The stress-reference definition, predictors, "
      "feature-selection rules, evaluation metrics and permitted recalibration strategy will be "
      "pre-specified in D1.2. The frozen model will subsequently be tested prospectively over two "
      "unseen commercial-field seasons. Performance will be evaluated using balanced accuracy, F1 and "
      "ROC-AUC for stress detection; reliability and Brier score for probabilistic calibration; and "
      "lead time and false-alarm rate for operational value. Regression metrics will be used only if "
      "the archive supports a defensible continuous stress-severity reference. Freezing the model and "
      "predictor definitions at M3 prevents retrospective optimisation against prospective outcomes and "
      "makes the central hypothesis directly falsifiable: whether water-stress relationships learned "
      "from controlled experimental observations remain valid when corresponding predictors are "
      "obtained from actual Sentinel-2 observations under commercial-field conditions.")

    edit(edit_id="E05", findings=("F-17",), answers=("R13", "R07"), target="§1.1 ¶Realistically achievable",
         change="Archive familiarity pointer (A-09) added once; CUT-18 and two duplicates removed (IPC-1).",
         cuts=("CUT-18",), dependencies="Training stays are detailed once, in §1.4.")
    S(P("Realistically achievable."),
      "**Realistically achievable.** The existing five-season MATE processing-tomato archive and "
      "controlled irrigation experiments support feasibility, and the fellow’s 2025 MATE training "
      "stays and co-authored processing-tomato manuscript (Section 1.4) mean the M1 archive audit starts "
      "from familiarity rather than first contact. Prospective validation covers one commercial "
      "environment, two growing seasons and controlled irrigation contrasts; DrR builds on an existing "
      "prototype. In-action validation remains limited to processing tomato; a crop-transfer "
      "specification and subsequent post-project replication and knowledge transfer through MVCRI "
      "address additional crops.")

    # ======================= 1.2 =======================
    edit(edit_id="E06", findings=("F-02",), answers=("R02",), target="§1.2 ¶Overall methodology",
         change="Physiological stress reference defined before fitting (primary axis, corroborating "
                "endpoint, fluorescence role, reference limits, indeterminate class, safe response); "
                "CUT-22 applied.", cuts=("CUT-22",))
    S(P("Overall methodology: concepts, models and assumptions."),
      "**Overall methodology: concepts, models and assumptions.** Four linked criteria evaluate "
      "water-stress prediction: physiological validity, predictive performance, transferability and "
      "management relevance. Irrigation treatments and AquaCrop water balances supply the "
      "imposed-deficit context and agronomic comparators, not the outcome, which would be circular. "
      "D1.2 fixes the stress reference before any fitting. Its primary axis is stomatal conductance "
      "relative to stage- and campaign-matched well-watered controls, corroborated by leaf water "
      "status or another consistently available independent marker deviating beyond its repeatability "
      "limit; chlorophyll fluorescence is complementary evidence, and a normal Fv/Fm alone does not "
      "label a plant unstressed. Reference limits derive from historical controls and measurement "
      "repeatability, never from model accuracy or prospective outcomes; ambiguous or confounded "
      "area-dates are classified indeterminate and retained in sensitivity reporting. Without a common "
      "two-marker reference across the archive, one continuous physiological endpoint becomes the "
      "primary reference and other measurements corroborate it.")

    edit(edit_id="E07", findings=("F-01", "F-03"), answers=("R01", "R03"), target="§1.2 ¶Stage 1 (WP1)",
         change="Restricted common-predictor chain (M1 audit, band integration with versioned SRFs, band "
                "exclusion, separated corrections, Level-2A, 20 m grid, pixel rules, engineering screen, "
                "failed-transfer response), named model/benchmark, leave-one-year-out validation, "
                "group-aware uncertainty, abstention, freeze rule and project decision criteria.",
         dependencies="ELTE secondment sentence compressed (IPC-3); D1.3 renumbering.")
    S(P("Stage 1 (WP1)"),
      "**Stage 1 (WP1) harmonises the 2022–2026 MATE archive into a QC-controlled common-variable "
      "matrix with explicit missingness and availability maps.** An M1 audit records per season the "
      "instrument, wavelength coverage, calibration, footprint, plot geometry, canopy, treatments, "
      "dates and matched physiology (D1.1). Historical plots are too small for plot-level Sentinel-2 "
      "retrieval, so calibrated canopy reflectance is integrated with versioned Sentinel-2 "
      "spectral-response functions into synthetic band reflectance, indices are computed after band "
      "integration, and bands outside the instrument’s range are dropped, not reconstructed. Proximal "
      "white/dark-reference correction stays separate from satellite atmospheric processing; "
      "Sentinel-2 inputs are cloud/shadow-masked Level-2A surface reflectance on a common 20 m grid "
      "where 20 m bands are used, with interior-pixel rules (≥90% treatment cover per pixel, ≥4 valid "
      "pixels per area and date). A predictor is retained only if it passes the D1.2 engineering "
      "screen (median absolute index discrepancy ≤0.25 historical standard deviations, ≤10% change in "
      "stress classifications on a locked sensitivity set); otherwise the model uses the defensible "
      "common predictors alone, a pre-specified soil-water/meteorological baseline is retained and the "
      "failed spectral transfer is reported. The primary model is a regularised logistic regression "
      "on a limited pre-specified predictor set, benchmarked against constrained gradient-boosted "
      "trees; outer leave-one-year-out validation across the five seasons tests temporal transfer, "
      "with imputation, scaling, feature selection, tuning and calibration fitted only inside training "
      "folds under year- and group-aware inner splits, uncertainty treated group-aware or "
      "hierarchically (each treatment area’s observations kept together; seasons reported separately "
      "and pooled), and abstention or a limited-evidence flag for out-of-domain or low-quality "
      "observations. The pipeline is selected under a declared historical-data rule, refitted on "
      "historical data only and frozen with its model card at M3 (D1.3), before use of any "
      "prospective-field outcome. D1.2 also fixes the decision criteria: balanced accuracy ≥0.70 with "
      "a demonstrated advantage over a locked agronomic comparator, positive Brier skill against a "
      "frozen reference model, an alert threshold set on historical predictions for sensitivity ≥0.80 "
      "at a false-positive rate ≤0.20, and interval-bounded lead time where observation frequency "
      "does not support a point estimate; failing a criterion restricts the model to research-only "
      "use and the MVP accordingly, and unchanged-model results are always reported before any "
      "separately versioned recalibration.")

    edit(edit_id="E08", findings=("F-02", "F-03"), answers=("R02", "R01"), target="§1.2 ¶Stage 2 (WP2) s2",
         change="Prospective design dimensioned (3 regimes × 4 blocks, 12 areas, 80 × 80 m, 20 m buffer, "
                "7.68 ha, 12 campaigns, 5 plants, 288 records, 202 pairs, growth-stage stratification, "
                "experimental unit, temporal not environmental replication); paired proximal spectra "
                "sentence appended; s1 and s4–s6 verbatim.", cuts=("CUT-19", "CUT-23", "CUT-25"),
         dependencies="§3.2 farmer row and risk R3 use the same design and field-readiness gate.")
    S(P("Stage 2 (WP2) prospectively tests"),
      "**Stage 2 (WP2) prospectively tests environmental and sensing-scale transfer over two "
      "processing-tomato seasons in an independent commercial field.** The adopted design, implemented "
      "subject to the field-readiness gate, has three irrigation regimes (well-watered, "
      "deficit-irrigated, unirrigated) in four spatial blocks: 12 separately managed, randomised "
      "treatment areas per season of about 80 × 80 m, a 20 m inward buffer leaving a 40 × 40 m "
      "interior core, and about 7.68 ha before access and isolation land. Twelve physiological "
      "campaigns per season across canopy development, flowering/fruit set, fruit filling and "
      "ripening, with temperature/VPD, genotype, time of day and competing stresses logged, sample "
      "five spatially distributed plants per area. The separately managed area is the experimental "
      "unit (plants, pixels and repeated dates are not independent replicates): up to 288 area-date "
      "records before missingness, about 202 area-date pairs under 30% attrition, and two years on one "
      "field give temporal replication, not two independent environments. The frozen model uses "
      "actual Sentinel-2 indices, soil-water and meteorological observations; coordinated physiology "
      "independently verifies realised plant stress. Primary performance precedes any recalibration; "
      "subsequent limited recalibration is secondary and pre-specified. The transfer gap quantifies "
      "predictive validity retained from controlled experiments to genuine satellite-scale field "
      "monitoring (**D2.1–D2.2, M20–M21**). Crop transfer is addressed separately, distinguishing "
      "reusable components from those requiring crop-specific recalibration and revalidation. Paired "
      "proximal canopy spectra on selected campaigns, aligned with Sentinel-2 observations and "
      "physiology, diagnose sensing discrepancies without tuning the frozen model; if sensing and "
      "environmental effects cannot be separated, the combined gap is reported and the claim narrowed.")

    edit(edit_id="E09", findings=("F-11",), answers=("R08",), target="§1.2 ¶Stage 3 (WP3–WP4)",
         change="Condensed to one sentence (CUT-12) to fund the §2.3 magnitude statement.", cuts=("CUT-12",))
    S(P("Stage 3 (WP3–WP4)"),
      "**Stage 3 (WP3–WP4)** operationalises only validated functions: the fellow’s pre-existing DrR – "
      "Digital Agronomist research prototype is extended with validated scientific functionality, "
      "Krumatic implements it and AgroVIR evaluates operational usability and interoperability.")

    edit(edit_id="E09a", findings=("F-11",), answers=("R08",), target="§1.1 ¶Problem (scope sentence)",
         change="Crop-transfer scope sentence compressed to a pointer; the one-crop/two-season limit stays "
                "in 'Realistically achievable' and Stage 2 (IPC-8).")
    edit(edit_id="E10", findings=("F-02",), answers=("R02",), target="§1.2 ¶Methodological challenges",
         change="Items (i)–(vi) verbatim; the two UAV sentences removed (CUT-19, allocated to E08); "
                "UAV's supplementary status stays in risk R4 and the §3.2 ELTE row.")
    S(P("Methodological challenges and mitigation."),
      "**Methodological challenges and mitigation.** (i) A year-by-variable availability matrix and "
      "only defensible common predictors manage inter-annual archive heterogeneity; **(ii)** pre-model "
      "spectral harmonisation and prospective scale-transfer testing link hyperspectral and satellite "
      "observations without assuming interchangeability; **(iii)** blocked unseen-year validation "
      "avoids optimistic random-split generalisation; **(iv)** a model frozen before deployment tests "
      "commercial-field transfer, reporting performance before recalibration; (v) sufficiently large "
      "treatment areas and valid interior observations reduce Sentinel mixed-pixel risk; and **(vi)** "
      "parsimony, uncertainty assessment, lead time and false-alarm rate control over-fitting. A "
      "predefined site-contingency plan protects two-season field validation.")

    edit(edit_id="E11", findings=("F-06",), answers=("R05", "R01"), target="§1.2 ¶Integration of methods",
         change="Discipline list and partner roles merged into accountabilities (Janda: physiology and "
                "scientific gates; Jung: sensor harmonisation; Hollós: statistical design, calibration, "
                "leakage checks; Takács: agronomic review of the irrigation protocol) (CUT-9, IPC-4).",
         cuts=("CUT-9",))
    S(P("Integration of methods and disciplines."),
      "**Integration of methods and disciplines.** HUN-REN ATK supplies plant-stress physiology and "
      "the scientific gates (Prof. Janda) and statistical design, calibration and leakage checks (Dr "
      "Hollós); ELTE sensor harmonisation and sensing-scale transfer (Prof. Jung); MATE the "
      "controlled-irrigation archive and agronomic review of the irrigation protocol before lock (Dr "
      "Takács); Krumatic/AgroVIR software-engineering and operational farm-management perspectives. "
      "The fellow integrates these disciplines: the biological reference constrains model "
      "interpretation, the protocol constrains development, and the validated predictor specification "
      "governs operational field inputs.")

    edit(edit_id="E12", findings=("F-04", "F-15"), answers=("R11",), target="§1.2 ¶Open science practices",
         change="Compact release plan: timestamped protocol registration, public protocol/metadata "
                "deposit, versioned model card, Zenodo or equivalent, BSD-3-Clause research code, "
                "metadata/synthetic examples where data are restricted, rights-cleared prospective "
                "dataset, preprints, negative results, layer separation, 30-day disclosure review "
                "subject to institutional clearance.", dependencies="D1.3 renumbering.")
    S(P("Open science practices"),
      "**Open science practices.** FIELDWISE follows the principle **“as open as possible, as closed as "
      "necessary.”** The stress-reference rules, predictor definitions, metrics, acceptance criteria "
      "and freeze record (D1.2) are registered with a timestamp before model fitting and deposited "
      "publicly with their metadata; D1.3 carries a versioned model card (intended use, validation, "
      "uncertainty, limitations). Deposits go to Zenodo or an equivalent repository with persistent "
      "identifiers; separable research code is released under BSD-3-Clause where ownership "
      "and dependencies permit, and metadata, access terms and synthetic examples are published where "
      "raw or background data cannot be. The prospective dataset and transfer analysis (D2.1–D2.2) are "
      "released in rights-cleared, non-identifying form; manuscripts are posted as preprints on "
      "submission where permitted, and successful and unsuccessful transfer results are both "
      "reported. A FAIR Data Management Plan is completed within six months. The scientific evidence "
      "package stays separate "
      "from the proprietary DrR, contractor code and FMIS layers; a 30-day project disclosure review, "
      "subject to mandatory institutional clearance, bounds the assessment of protectable results "
      "before release.")

    # ======================= 1.3 =======================
    edit(edit_id="E13", findings=("F-06",), answers=("R05",), target="§1.3 ¶Supervisory architecture",
         change="Generic opener removed (IPC-5); host EU-project sentence replaced (CUT-10) by sourced "
                "supervision evidence (Janda: doctoral-school roles, 1997–2012 teaching, 2023 "
                "co-supervision example, research stays; Jung: doctoral-programme head, named courses, "
                "Halle-Wittenberg/Leipzig/Ulm experience) and accountabilities; no totals invented.",
         cuts=("CUT-10",))
    S(P("Supervisory architecture and qualifications"),
      "**Supervisory architecture and qualifications.** Primary supervision at the recruiting "
      "organisation, HUN-REN ATK, is provided by **Prof. Tibor Janda**, Head of the Plant Physiology "
      "and Metabolomics Department at the Agricultural Institute, accountable for the physiological "
      "reference and the scientific gates. His plant-physiology, drought/abiotic-stress and "
      "stress-metabolomics expertise anchors the physiological-validation framework and the "
      "measurement programme. His supervision record is documented: doctoral-school core member since "
      "2010 and council member since 2013, lecturer in "
      "plant physiological investigation methods (1997–2012), co-supervisor of a 2023 doctoral "
      "dissertation at Széchenyi István University, and research stays at CEA Saclay and Ben-Gurion "
      "University. **Dr Roland Hollós** (ATK) is accountable for statistical design, calibration and "
      "leakage checks in the predictive-modelling and machine-learning strand[^5]. **Prof. András Jung "
      "(ELTE, Institute of Cartography and Geoinformatics)** provides specialist co-supervision in field "
      "spectroscopy, hyperspectral imaging, geoinformatics, satellite Earth observation and sensor "
      "harmonisation[^6], is a doctoral-programme head at ELTE and has research and teaching experience "
      "at Halle-Wittenberg, Leipzig and Ulm. MATE contributes the five-season "
      "controlled-irrigation processing-tomato archive and agronomic expertise through **Dr Sándor "
      "Takács**, including AquaCrop-based irrigation and crop-water-stress methodology.")

    edit(edit_id="E14", findings=("F-07", "F-13", "F-14"), answers=("R06", "R10"),
         target="§1.3 ¶Planned training activities and ELTE secondment",
         change="Timed, assessed training schedule with named providers and ELTE courses; M1–M3 "
                "primary-supervision continuity (weekly meetings, fortnightly joint sessions, shared "
                "records, joint sign-off, continuity/deputy arrangement without a named deputy); "
                "deliverable-backed teaching with host seminar otherwise; CDP cadence reconciled "
                "(CUT-23 removed here, allocated to E08).",
         dependencies="§2.1 table cadence identical; §3.1 T5.1 keeps 'quarterly reviews'.")
    S(P("Planned training activities and ELTE secondment."),
      "**Planned training activities and ELTE secondment.** Training is embedded in implementation "
      "and assessed by output: M1–M3 at ELTE (Prof. Jung), a supervised module on the ELTE subjects "
      "Hyperspectral Imaging and Field Spectroscopy and Remote Sensing Methods and Technologies "
      "(output: reproducible band-integration/QC notebook); M1–M3 at ATK (Prof. Janda, Dr Takács), "
      "physiological-reference and irrigation-design practical (reviewed reference protocol, "
      "repeatability exercise); M1–M3 and M10–M12 at ATK (Dr Hollós), blocked validation, calibration "
      "and uncertainty practical (rerun historical folds, model-card review); M4–M9, host "
      "research-support staff, reproducible research, FAIR data, responsible generative-AI use and IP "
      "(release package, DMP); M16–M21 at ELTE, paired-sensing and transfer-diagnostics clinic; "
      "M22–M30, ATK support and AgroVIR, grant-writing clinic and FMIS evaluation (Section 2.1). The "
      "12-month ELTE secondment (M1–M3, M10–M12, M16–M21) hosts the EO strands. During M1–M3, "
      "primary supervision continues through weekly Janda–fellow meetings, fortnightly joint "
      "physiology/EO/modelling sessions, shared versioned records and a joint sign-off before protocol "
      "lock and model freeze; a documented continuity arrangement designates a deputy for prolonged "
      "absence. Teaching: an ATK/ELTE practical on physiological validation by M12 and a "
      "transfer-analysis practical by M24; guest lectures at MATE or the Agricultural "
      "University–Plovdiv when scheduled, a host seminar otherwise. The **Career Development Plan "
      "(D5.1, M3)** consolidates the programme and the transferable-skills portfolio (Section 2.1), "
      "reviewed quarterly (M6–M30) with transition reviews at M12/M21/M24/M27.")

    edit(edit_id="E15", findings=("F-13",), answers=("R06", "R10"), target="§1.3 ¶Two-way transfer",
         change="Generic opening sentence cut (CUT-20); s2–s4 verbatim.", cuts=("CUT-20",))
    S(P("Two-way transfer of knowledge."),
      "**Two-way transfer of knowledge.** HUN-REN ATK contributes advanced abiotic-stress physiology, "
      "phenotyping and modelling; ELTE established hyperspectral-sensing, geoinformatics and "
      "satellite-EO expertise. The fellow contributes drought-stress physiology, remotely monitored "
      "plant-stress responses, field physiological phenotyping and interpretation under contrasting "
      "water availability, strengthening stress biology’s translation into irrigation decision support. "
      "Joint supervision, the distributed ELTE secondment, shared MATE-archive analysis, prospective "
      "field validation, teaching and co-authored publications reinforce exchange.")

    edit(edit_id="E16", findings=("F-11",), answers=("R08",), target="§1.3 ¶Rationale and added value",
         change="s6 cut (CUT-11); s1–s5 and the final arrangements sentence verbatim.", cuts=("CUT-11",))
    S(P("Rationale and added value of the non-academic placement."),
      "**Rationale and added value of the non-academic placement.** The six-month AgroVIR placement "
      "(M25–M30) is an integral inter-sectoral component of FIELDWISE, providing competences not fully "
      "available academically: DrR web-MVP operational evaluation, FMIS requirements engineering, "
      "interoperability assessment, user-oriented testing and exploitation planning. AgroVIR supplies "
      "requirements feedback during the fellowship; the placement adds intensive exposure to production "
      "agricultural software and decision-support workflows. Structured technical reviews assess "
      "usability, data-flow requirements, missing-data behaviour, interoperability and the pathway "
      "toward future FMIS integration. Confidentiality, DrR background access and result ownership are "
      "defined in advance under the Grant Agreement (Section 2.2).")

    # ======================= 1.4 =======================
    edit(edit_id="E17", findings=("F-08", "F-10"), answers=("R07",), target="§1.4 ¶A profile matched",
         change="Three competence-to-task links (physiology; EO/data science via the 2025 MATE stays and "
                "2026 ELTE traineeship; recent crop work with the 2025 proceedings paper and two 2026 "
                "manuscripts labelled under review); DrR as a pre-existing desktop research prototype; "
                "disputed MSc omitted; undated/unnamed items and duplicated fit sentences removed (IPC-6).",
         dependencies="Consumes CUT-1 (career duplicate in §1.1).")
    S(P("A profile matched to the project"),
      "**A profile matched to the project’s interdisciplinary chain.** Dr. Rositsa Cholakova "
      "(publishing before 2020 as Rositsa Cholakova-Bimbalova) holds BSc and MSc degrees in Plant "
      "Protection and a PhD in Plant Physiology (2020, Agricultural University of Plovdiv). She was "
      "Assistant Professor in Plant Physiology and Plant Stress Physiology in Plovdiv (2015–2020) and "
      "is currently Chief Assistant Professor at the Maritsa Vegetable Crops Research Institute. "
      "**Physiology:** her published maize "
      "stress-physiology work and documented methods (chlorophyll fluorescence, stomatal conductance, "
      "pigment and leaf water status, field stress assessment) equip her to define and measure the "
      "independent physiological reference. **Earth "
      "observation and data science:** a COST PANGEOS Short-Term Scientific Mission at MATE (10 days, "
      "2025), Erasmus+ RGB/hyperspectral training at MATE (14 days, 2025) and a three-month ELTE "
      "traineeship in geoinformatics and remote sensing (2026), with working use of Python, R and "
      "EO tools, prepare her for the archive audit, band integration and Sentinel-2 processing. "
      "**Recent crop work:** a 2025 proceedings paper on "
      "remote-sensing monitoring of watermelon under different water regimes and two 2026 manuscripts, "
      "under review, on UAV-based evapotranspiration in tomato fields and on proximal hyperspectral "
      "signatures of water stress in processing tomato with physiological and soil-water validation, "
      "the latter co-authored with Dr Takács (Part B-2, Section 4). She holds an EU A1/A3 drone-pilot "
      "qualification and developed **DrR – Digital Agronomist**, a pre-existing desktop research "
      "prototype that FIELDWISE extends only with validated functions. Five years of university "
      "teaching in Bulgarian and English underpin the teaching strand. **Fit and "
      "development potential.** The fellowship addresses the next "
      "step in her progression: advanced predictive modelling, uncertainty analysis, leakage-safe "
      "validation and transfer across years, sensing scales and commercial-field conditions, deepened "
      "through the distributed ELTE secondment and specialist supervision at HUN-REN ATK. Following a "
      "full-time-parenting career break (2021–2024), she has re-entered research with a focused "
      "transition toward an independent **Agricultural Data Scientist working at the interface of "
      "plant physiology, Earth observation and irrigation decision support**.")

    # ======================= 2.1 =======================
    edit(edit_id="E18", findings=("F-12",), answers=("R09",), target="§2.1 ¶FIELDWISE is designed",
         change="s2 cut (CUT-13); s1 verbatim.", cuts=("CUT-13",))
    S(P("FIELDWISE is designed to consolidate"),
      "FIELDWISE is designed to consolidate the fellow’s transition from plant-stress physiologist and "
      "agronomist to an **independent Agricultural Data Scientist working at the interface of plant "
      "physiology, Earth observation, predictive modelling and irrigation decision support**.")
    edit(edit_id="E18a", findings=(), answers=(), target="§2.1 ¶Two realistic trajectories",
         change="Record clause compressed (IPC-8); the two trajectories and K11 unchanged.")
    S(P("Two realistic post-fellowship trajectories"),
      "**Two realistic post-fellowship trajectories anchor this development.** The first is an "
      "independent research/data-science role in European academia, research organisations or "
      "agri-technology. The second is development of an independent research and innovation line in "
      "Bulgaria, "
      "extending the FIELDWISE methodology to further irrigated high-value crops and transferring the "
      "acquired competences through MVCRI. Progress is tracked through the Career Development Plan and "
      "career KPI **K11**.")

    t21 = lib.find_table(doc, "Measure")
    edit(edit_id="E19", findings=("F-14",), answers=("R10",), target="§2.1 table, Career Development Plan row",
         change="Evidence cell reconciles quarterly reviews (M6–M30) with transition reviews M12/M21/M24/M27; D5.1 stays at M3.")
    lib.set_cell_markup(lib.row_cells(lib.find_row(t21, "Career Development Plan"))[2],
                        "D5.1 (M3); quarterly reviews M6–M30; transition reviews M12/M21/M24/M27; K11")
    edit(edit_id="E20", findings=("F-23",), answers=("R16", "R06"), target="§2.1 table, ATK training and ELTE secondment rows",
         change="The two training rows merged into one (ATK modelling training and the 12-month ELTE "
                "secondment); evidence cell D1.4 → D1.3 (IPC-9).")
    row = lib.find_row(t21, "ATK scientific and modelling training")
    lib.set_cell_markup(lib.row_cells(row)[0], "**ATK modelling training and 12-month ELTE secondment**")
    lib.set_cell_markup(lib.row_cells(row)[1],
                        "ATK: plant-stress interpretation, experimental design, interpretable modelling, "
                        "leakage-safe validation, calibration and uncertainty. ELTE (M1–M3, M10–M12, M16–M21): "
                        "hyperspectral-to-Sentinel harmonisation, geoinformatics, EO processing and "
                        "sensing-scale transfer, applied first to historical predictors and then to real "
                        "Sentinel-2 field observations.")
    lib.set_cell_markup(lib.row_cells(row)[2], "Supervision records; model card; D1.3; secondment outputs; CDP")
    lib.delete_row(lib.find_row(t21, "12-month distributed ELTE secondment"))
    edit(edit_id="E21", findings=("F-13",), answers=("R10",), target="§2.1 table, Transferable-skills row",
         change="Three dated independence measures added: methods clinic by M12; complete grant concept "
                "and mock-reviewed application by M21–M24 (submission only if an eligible call is open; no "
                "award promised); mentoring M10–M21 with peer-learning/teaching-practical fallback.")
    row = lib.find_row(t21, "Transferable-skills portfolio")
    lib.set_cell_markup(lib.row_cells(row)[1],
                        "Research integrity, FAIR/open science, responsible AI, grant writing, IP, project "
                        "management and science communication, exercised through FIELDWISE. Independence "
                        "measures: lead a methods clinic by M12; prepare a grant concept and mock-reviewed "
                        "application by M21–M24; mentor a junior researcher or student on a reproducible "
                        "analysis task in M10–M21 (peer-learning group if no mentee).")
    lib.set_cell_markup(lib.row_cells(row)[2],
                        "CDP-tracked: clinic (M12), reviewed application (M24), mentoring record (M21)")
    edit(edit_id="E22", findings=("F-13",), answers=("R10",), target="§2.1 table, Scientific visibility row",
         change="Teaching venues and the COST Action CA22136 PANGEOS contact base named as the networking starting point (A-16).")
    lib.set_cell_markup(lib.row_cells(lib.find_row(t21, "Scientific visibility and leadership"))[1],
                        "Co-authored publications, conference presentations, seminars and guest lectures at "
                        "MATE and the Agricultural University–Plovdiv, and the COST Action CA22136 PANGEOS "
                        "contact base, build visibility, networks and future supervision capacity.")

    edit(edit_id="E23", findings=("F-11",), answers=("R08",), target="§2.1 ¶By completion",
         change="s3 cut (CUT-8); rest verbatim.", cuts=("CUT-8",))
    S(P("By completion, the fellow will have taken"),
      "By completion, the fellow will have taken one research concept through biological definition, "
      "historical-data **harmonisation, predictive modelling, unseen-year validation, prospective "
      "satellite-based field validation, software translation and industrial evaluation**, a "
      "combination that strengthens employability across academic plant/EO research, agricultural "
      "data science and agri-technology.")

    # ======================= 2.2 =======================
    edit(edit_id="E24", findings=("F-12",), answers=("R09",), target="§2.2 ¶FIELDWISE uses a targeted strategy",
         change="s2 cut (CUT-17); the table's target-group column carries the audiences.", cuts=("CUT-17",))
    S(P("FIELDWISE uses a targeted strategy"),
      "FIELDWISE uses a targeted strategy proportionate to a single-fellow action, progressing from "
      "scientific dissemination → practitioner communication → operational and entrepreneurial "
      "exploitation.")
    t22 = lib.find_table(doc, "Strand")
    edit(edit_id="E25", findings=("F-15", "F-23"), answers=("R11", "R16"), target="§2.2 table, Dissemination row",
         change="Irrigation Science / ISHS venue added beside EGU/ECPA; release assets named; D1.4 → D1.3.")
    row = lib.find_row(t22, "Dissemination")
    lib.set_cell_markup(lib.row_cells(row)[2],
                        "≥2 peer-reviewed manuscripts, possible third; model card; hyperspectral-to-Sentinel/"
                        "transfer methodology; prospective transfer performance published, successful or not; "
                        "EGU/ECPA and an Irrigation Science paper or ISHS irrigation symposium; registered "
                        "protocol, metadata, separable code and non-sensitive outputs released with "
                        "persistent identifiers.")
    lib.set_cell_markup(lib.row_cells(row)[3], "D1.3 M3; D2.1 M20; D2.2 M21")
    edit(edit_id="E26", findings=("F-12",), answers=("R09",), target="§2.2 table, Communication row",
         change="Per audience: main message, tool, timing and evidence (practitioner brief M12, two "
                "demonstrations M25–M29, workshop of about 20 participants M29–M30, three explainers "
                "M3/M12/M24, one tutorial and HU/BG summaries M21–M24); evidence cell names attendance, "
                "feedback, views and downloads under project control.")
    row = lib.find_row(t22, "Communication")
    lib.set_cell_markup(lib.row_cells(row)[1], "Growers and advisors (HU/BG); wider public; HU/BG students and practitioners")
    lib.set_cell_markup(lib.row_cells(row)[2],
                        "Growers/advisors: what an uncertainty-qualified alert means and when no advice is "
                        "justified; practitioner brief (M12), two demonstrations at the AgroVIR evaluation "
                        "(M25–M29), one workshop of about 20 participants (M29–M30). Public: why plants, "
                        "satellites and uncertainty are checked together before advice; three illustrated "
                        "explainers (M3, M12, M24). Students/practitioners (HU/BG): which methods transfer "
                        "and which need local validation; one reusable tutorial and Hungarian/Bulgarian "
                        "summaries (M21–M24). Claims restricted to measured evidence.")
    lib.set_cell_markup(lib.row_cells(row)[3],
                        "Attendance, feedback, views and downloads; reported in D5.3")

    edit(edit_id="E27", findings=("F-11", "F-12"), answers=("R08", "R09"), target="§2.2 ¶Reach and uptake",
         change="Project-controlled reach indicators with the adopted targets (6–10 growers/advisors, 2–3 "
                "FMIS users, two demonstrations, one workshop, three explainers, one tutorial, two "
                "summaries); recruitment through AgroVIR stated as a target, attendance not equated with adoption.")
    S(P("Reach and uptake are tracked"),
      "Reach and uptake are tracked through project-controlled evidence: ≥2 conference presentations "
      "and submitted manuscripts; structured evaluation with 6–10 growers or advisors and 2–3 FMIS or "
      "technical users (task completion, uncertainty interpretation, usability); two demonstrations "
      "and one workshop with recorded attendance and feedback; three explainers, one tutorial and two "
      "language summaries; the AgroVIR assessment; repository downloads. AgroVIR recruitment is an "
      "agreed target, not a guaranteed channel; attendance is not adoption.")

    # ======================= 2.3 =======================
    edit(edit_id="E28a", findings=("F-11",), answers=("R08",), target="§2.3 intro",
         change="Duration sentence removed (stated in §1.3 and §3.1); the bounded-impact sentence kept.")
    S(P("FIELDWISE is a 24-month MSCA Postdoctoral Fellowship followed"),
      "Impact is bounded to what the action demonstrates directly: whether physiologically grounded "
      "water-stress relationships remain valid across unseen years, sensing scales and two prospective "
      "seasons, and whether validated results support operational decisions.")
    t23 = lib.find_table(doc, "Dimension")
    edit(edit_id="E28", findings=("F-11",), answers=("R08",), target="§2.3 table, Agricultural & environmental row",
         change="Water-saving boundary kept verbatim; added that irrigation, yield and quality are "
                "recorded by treatment and not used to estimate DrR-caused savings.")
    lib.set_cell_markup(lib.row_cells(lib.find_row(t23, "Agricultural & environmental"))[2],
                        "The direct value is more defensible identification of **when and where water "
                        "stress requires attention**. Warning lead time, false alarms, uncertainty and "
                        "water–yield–quality relationships are measured prospectively; no numerical "
                        "water-saving benefit is claimed in advance. Irrigation, yield and quality are "
                        "recorded by treatment, not used to estimate DrR-caused savings.")
    lib.set_cell_markup(lib.row_cells(lib.find_row(t23, "Scientific"))[2],
                        "Outputs: a documented model, quantified transfer performance and a specification "
                        "separating reusable from crop-/scale-specific components, showing **whether, how "
                        "far and under which conditions predictive validity survives transfer**.")
    edit(edit_id="E29", findings=("F-11",), answers=("R08",), target="§2.3 table, European & societal row",
         change="Row rewritten with the work-programme expected outcomes (skills and employability; "
                "international, inter-sectoral, interdisciplinary experience; knowledge exchange; "
                "research-to-teaching feedback) and the EU Water Resilience Strategy link without adopting "
                "its 10% ambition (A-12).")
    row = lib.find_row(t23, "European & societal")
    lib.set_cell_markup(lib.row_cells(row)[1],
                        "A Bulgarian researcher trained in Hungary across an academic host, a university "
                        "secondment host and a non-academic FMIS company, with a potential MVCRI continuation "
                        "route.")
    lib.set_cell_markup(lib.row_cells(row)[2],
                        "Serves the EU Water Resilience Strategy’s efficiency and digitalisation priorities "
                        "(its 10% economy-wide ambition is not a project target); delivers the call’s "
                        "fellowship outcomes: skills and employability, international/interdisciplinary/"
                        "inter-sectoral experience, knowledge exchange, research-to-teaching transfer, each "
                        "with an evidencing output.")
    edit(edit_id="E30", findings=("F-11",), answers=("R08",), target="§2.3 ¶Impact is measured",
         change="K1–K14 duplicate cut (CUT-7); three scales distinguished: direct delivery, AgroVIR's "
                "translation channel (over 700,000 ha, company-reported August 2025, attributed and "
                "bounded) and the narrower eligible-uptake group quantified during the placement and "
                "modelled only as a scenario.", cuts=("CUT-7",))
    S(P("Impact is measured through"),
      "Impact is measured through project-controlled evidence: discrimination and calibration, "
      "uncertainty, false alarms, warning lead time and prospective transfer performance, all "
      "pre-specified in D1.2 and reported before any limited recalibration. Three scales are kept "
      "distinct: direct delivery (one crop, one commercial environment over two seasons, one frozen "
      "model, one web MVP, one industrial evaluation); the "
      "translation channel, where AgroVIR reported in August 2025 that its software serves over "
      "700,000 ha across Hungary and six other countries, an established distribution context that is "
      "neither FIELDWISE coverage nor irrigated-tomato area, adoption or water saving; and eligible "
      "uptake, the subset of that network with suitable crop, irrigation, field-size and data "
      "conditions, quantified during the placement (denominator, date, definition), with later "
      "adoption modelled only as an explicit scenario after validation and a separate adoption "
      "decision.")

    # ======================= 3.1 =======================
    heading3 = P("3. Quality and Efficiency of the Implementation")
    heading3.paragraph_format.page_break_before = True
    # the sealed 3.2 heading carries no keep-with-next; without it the heading can strand at the
    # foot of the Gantt page
    P("3.2 Quality and capacity of the host institutions").paragraph_format.keep_with_next = True
    edit(edit_id="E31", findings=("F-21",), answers=("R17",), target="§3.1 ¶The fellow leads",
         change="s2 cut (CUT-14); Section 3 starts on a new page (layout target kept explicit).", cuts=("CUT-14",))
    S(P("The fellow leads the scientific work"),
      "The fellow leads the scientific work at the sole beneficiary, HUN-REN ATK (ATK), over 24 months, "
      "followed by the AgroVIR placement (M25–M30). ELTE secondment blocks are M1–M3, M10–M12 and "
      "M16–M21 (12 months); they are locations of work within the allocated effort. MATE supplies "
      "archive/irrigation expertise; the producer hosts field trials; Krumatic supplies remunerated "
      "engineering.")
    edit(edit_id="E32", findings=("F-23",), answers=("R16",), target="§3.1 WP1 deliverable line",
         change="D1.4 model/card → D1.3; D1.5 transfer specification → D1.4; K1–K4 verbatim.")
    S(P("D1.1 archive/QC map (M2)"),
      "D1.1 archive/QC map (M2); D1.2 protocol and D1.3 model/card (M3); D1.4 transfer specification "
      "(M21). K1–K4: five seasons audited; one locked protocol; reproducible, leakage-safe "
      "held-out-year results; one reusable/crop-specific transfer specification. Gates: MS1/MS3.")
    edit(edit_id="E33", findings=("F-18",), answers=("R13",), target="§3.1 WP2 deliverable line (K5)",
         change="K5 condensed (CUT-16) while keeping scheduled-versus-valid observation accounting.", cuts=("CUT-16",))
    S(P("D2.1 dataset/prediction log (M20)"),
      "D2.1 dataset/prediction log (M20); D2.2 transfer/uncertainty report (M21). K5: two seasons; "
      "scheduled versus valid observation opportunities and biological sample size reported. K6: "
      "season-level and pooled discrimination, calibration, false alarms, lead time and transfer gap, "
      "with uncertainty or non-estimability explained. Gates: MS1–MS3.")
    edit(edit_id="E34", findings=("F-14", "F-18"), answers=("R10", "R13"), target="§3.1 WP5 task line",
         change="T5.1–T5.4 condensed (CUT-15) keeping 'quarterly reviews' (A-33).", cuts=("CUT-15",))
    S(P("Lead: fellow/ATK; supervisors and host support services"),
      "**Lead:** fellow/ATK; supervisors and host support services contribute. **T5.1:** CDP, quarterly "
      "reviews, technical/transferable skills, knowledge exchange. **T5.2:** data/access rules from M1; "
      "DMP. **T5.3:** dissemination/communication/exploitation from M1; initial strategy at M3. "
      "**T5.4:** monthly progress/risk monitoring, agreements and reporting (all M1–M30).")
    edit(edit_id="E35", findings=("F-21",), answers=("R17",), target="§3.1 WP5 deliverable line",
         change="Administrative-outputs sentence cut (CUT-5); K11–K14 verbatim.", cuts=("CUT-5",))
    S(P("D5.1 CDP (M3); D5.2 DMP"),
      "D5.1 CDP (M3); D5.2 DMP (M6; review M21/M30); D5.3 final dissemination/exploitation plan (M30; "
      "update M24). K11: CDP reviews, four technical competence strands and 12 secondment months "
      "evidenced. K12: all released assets have metadata and access decisions. K13: ≥2 manuscripts "
      "submitted, ≥2 conference presentations and ≥1 end-user workshop by M30. K14: each result family "
      "has an owner, audience, route and indicators.")
    edit(edit_id="E36", findings=("F-17", "F-18"), answers=("R13",), target="§3.1 ¶Critical path",
         change="Assumed February start with M3 freeze before first principal observations and second "
                "harvest by M20; honest slipped-start response; effort rationale from the accepted "
                "allocation (pre-freeze WP1 2.2 PM, later 2.8 PM diagnostics; period totals kept).")
    S(P("Critical path:"),
      "**Critical path:** MS1 model freeze → WP2 prospective evidence → MS3 permitted functions → MS4 "
      "release → WP4 evaluation. The plan assumes a February start: MS1 in April (M3) precedes the "
      "first principal field observations in May (M4), and the second harvest falls by M20 "
      "(September). If the start slips, a feasible start is chosen within the permitted grant window "
      "before launch; field readiness is confirmed before interventions; a backup site is used only "
      "if genuinely available; if two complete seasons cannot fit, the action is formally rephased or "
      "the evidence claim narrowed, never another dataset relabelled as the primary test. WP effort "
      "totals 30.0 fellow PM: 24.0 in M1–M24 and 6.0 in M25–M30 (WP4 5.4; WP5 0.6). Pre-freeze WP1 "
      "effort is 2.2 PM of the 3.0 PM in M1–M3 (0.8 PM set up WP2/WP3/WP5); the remaining 2.8 PM are "
      "later transfer diagnostics and specification work (M10–M12, M16–M21), and standalone training, "
      "communication and software work stays out of the M16–M21 field season. Training within "
      "scientific tasks is counted once. Partner support is additional to these fellow PM.")

    trisk = lib.find_table(doc, "Risk; likelihood/impact")
    edit(edit_id="E37", findings=("F-21", "F-16"), answers=("R17", "R12"), target="§3.1 risk table",
         change="Six decision-specific rows (archive rights/coverage and model freeze; field/irrigation/"
                "calendar; sensors/cloud/pixels; poor transfer; supervisor/ELTE access; engineering/IP/"
                "placement) with distinct ratings; no backup site, deputy or substitute provider claimed "
                "to exist (brief R17 alternative: six rows with added triggers).")
    rows = list(trisk.rows)
    if len(rows) != 1 + len(RISK_ROWS):
        raise ValueError(f"risk table has {len(rows) - 1} rows, {len(RISK_ROWS)} texts given")
    for r, (c0, c1) in zip(rows[1:], RISK_ROWS):
        cells = lib.row_cells(r)
        lib.set_cell_markup(cells[0], c0)
        lib.set_cell_markup(cells[1], c1)
    for header, widths in TABLE_WIDTHS_CM.items():
        lib.set_column_widths(lib.find_table(doc, header), widths)

    # ======================= 3.2 =======================
    edit(edit_id="E38", findings=("F-16", "F-22"), answers=("R12", "R15"), target="§3.2 intro",
         change="Dependency statement (arrangements completed before the activity; nothing claimed as "
                "signed) and the resource-priority order (IPC-7).")
    S(P("The sole beneficiary and recruiting organisation"),
      "The sole beneficiary and recruiting organisation is HUN-REN ATK (facilities: Part B-2 Section "
      "5). Required data-use, service, secondment-access and field-operation arrangements are completed "
      "before the corresponding activity or access begins, and none is claimed as signed or held. "
      "Resources are prioritised in this order: independent physiological reference and replicated "
      "field design; soil-water, weather and irrigation monitoring; essential spectral/EO acquisition; "
      "the minimum scientifically valid web MVP; optional UAV work, interface polish, extra travel or "
      "events last.")
    t32 = lib.find_table(doc, "Organisation")
    edit(edit_id="E39", findings=("F-20",), answers=("R14",), target="§3.2 table, HUN-REN ATK row",
         change="Team-balance sentence cut (CUT-2); hosting plan with provision deadlines (induction, "
                "workspace, instruments, workstation and secure storage, remote EO access, HR/data/IP/"
                "grants support) without inventing allocations.", cuts=("CUT-2",))
    lib.set_cell_markup(lib.row_cells(lib.find_row(t32, "HUN-REN ATK"))[1],
                        "HUN-REN research organisation, Martonvásár, with the fellowship anchored in the "
                        "Agricultural Institute. **Prof. Tibor Janda is the primary supervisor** "
                        "(plant-stress physiology, phenotyping, abiotic stress); **Dr Roland Hollós** "
                        "supports the predictive-modelling/ML strand. Hosting plan: the fellow joins the Plant "
                        "Physiology and Metabolomics Department as an employed researcher; M1 induction covers "
                        "workspace, laboratory and instrument access, a workstation with secure versioned "
                        "project storage and remote access to EO processing during ATK months; HR "
                        "onboarding, reimbursement, data/IP and grants support come from the host’s "
                        "administration, each in place before first use.")
    edit(edit_id="E40", findings=("F-16",), answers=("R12", "R06"), target="§3.2 table, ELTE row",
         change="Team-balance sentence cut (CUT-3); planned secondment tasks per block; access arranged "
                "before each block, no allocated instrument time claimed.", cuts=("CUT-3",))
    lib.set_cell_markup(lib.row_cells(lib.find_row(t32, "ELTE"))[1],
                        "Institute of Cartography and Geoinformatics: hyperspectral sensing, geoinformatics, "
                        "Earth observation and sensing-scale transfer. **Prof. András Jung is the "
                        "co-supervisor and secondment supervisor.** The **12-month research secondment is "
                        "distributed across the 24-month fellowship**: band-integration and QC notebook "
                        "(M1–M3), transfer diagnostics (M10–M12) and the paired-sensing clinic (M16–M21), with "
                        "instrument and operator access arranged before each block. **Dr Zsófia Varga** "
                        "supports targeted UAV acquisition where required and feasible; UAV observations "
                        "remain supplementary and do not replace Sentinel-2 in the primary transferability "
                        "assessment.")
    edit(edit_id="E41", findings=("F-16",), answers=("R12",), target="§3.2 table, MATE row",
         change="M1 archive and rights audit; only the legally accessible common subset used; no access "
                "terms or redistribution rights claimed.")
    lib.set_cell_markup(lib.row_cells(lib.find_row(t32, "MATE"))[1],
                        "Provides the **2022–2026 controlled-irrigation processing-tomato archive**, including "
                        "soil-water, physiological, spectral, meteorological and agronomic observations. **Dr "
                        "Sándor Takács** contributes processing-tomato irrigation and AquaCrop expertise, while "
                        "**Prof. Gábor Milics** contributes precision-agriculture expertise. An M1 archive and "
                        "rights audit fixes the accessible years, variables and permitted analysis; only the "
                        "legally accessible common subset is used, and redistribution or commercial reuse is "
                        "not assumed.")
    edit(edit_id="E42", findings=("F-16", "F-22"), answers=("R12", "R15"), target="§3.2 table, Krumatic row",
         change="Deliverable-based engineering scope contracted before paid development; lean-MVP fallback; "
                "no quotation, contract or funding allocation claimed.")
    lib.set_cell_markup(lib.row_cells(lib.find_row(t32, "Krumatic"))[1],
                        "Krumatic provides **paid specialist software-engineering services** for implementation "
                        "of the DrR web MVP from the fellow’s pre-existing desktop research prototype; "
                        "scientific specifications, model validation and interpretation remain with the "
                        "fellow/HUN-REN ATK. A deliverable-based scope (ingestion, provenance, frozen-model "
                        "inference, uncertainty display, acceptance tests, source delivery and rights) is "
                        "contracted before paid development; a lean MVP contingency defers dashboards and "
                        "production FMIS integration.")
    edit(edit_id="E43", findings=("F-16", "F-02"), answers=("R12", "R02"), target="§3.2 table, Commercial farmer row",
         change="Adopted field requirements and the field-readiness gate stated; no site named or described as secured.")
    lib.set_cell_markup(lib.row_cells(lib.find_row(t32, "Commercial farmer"))[1],
                        "An independent Hungarian **farmer/producer, irrespective of gender**, provides the "
                        "commercial field for **two prospective seasons** and implements the agreed treatments "
                        "and routine management under the field protocol. Adopted "
                        "requirements, decided at the field-readiness gate before planting: 12 separately "
                        "managed treatment areas with independently controllable water delivery, "
                        "Sentinel-2-valid interior cores and two-season availability; no site is described "
                        "as secured. The project installs soil-water and meteorological monitoring and "
                        "conducts all specialised observations; design, validation, analysis and "
                        "interpretation remain with the fellow/HUN-REN ATK.")
    edit(edit_id="E44", findings=("F-16",), answers=("R12", "R08"), target="§3.2 table, MVCRI row",
         change="Condensed (CUT-4) to a potential continuation route; not a guaranteed position, funded "
                "activity or multi-crop programme; protected sentence kept.", cuts=("CUT-4",))
    lib.set_cell_markup(lib.row_cells(lib.find_row(t32, "MVCRI"))[1],
                        "**Prof. Ganeva** supports a potential post-MSCA continuation route at MVCRI for "
                        "crop-specific recalibration and transfer to Bulgarian production conditions; it is "
                        "not a guaranteed position, funded activity or multi-crop validation programme. "
                        "**MVCRI has no core in-action validation role during the project.**")


# ---------------------------------------------------------------------------
# Build, validate, export, report
# ---------------------------------------------------------------------------
GANTT_SIZE_PX = (2125, 760)  # sealed image is 2125 x 975 px at 17.99 cm; same width, 22% shorter
TABLE_FONT_HALF_PTS = 20  # 10 pt table text (permitted minimum 8 pt; body text stays 11 pt)
GANTT_EXTENT_CX = 6477000  # EMU, unchanged
GANTT_EXTENT_CY_OLD = 2971800  # EMU in the sealed drawing (unique to the Gantt drawing)


def build_docx(out_path: Path = OUT_DOCX, gantt_png: Path = GANTT_PNG) -> Path:
    EDITS.clear()
    doc = Document(str(BASELINE_DOCX))
    apply_edits(doc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    lib.build_gantt_png(gantt_png, GANTT, size_px=GANTT_SIZE_PX)
    gantt_bytes = gantt_png.read_bytes()
    new_cy = round(GANTT_EXTENT_CX * GANTT_SIZE_PX[1] / GANTT_SIZE_PX[0])

    def document(data: bytes) -> bytes:
        old = f'cy="{GANTT_EXTENT_CY_OLD}"'.encode()
        if data.count(old) != 2:  # wp:extent and a:ext of the Gantt drawing
            raise ValueError(f"Gantt extent found {data.count(old)} times, expected 2")
        return data.replace(old, f'cy="{new_cy}"'.encode())

    def styles(data: bytes) -> bytes:
        # Table text set to TABLE_FONT_HALF_PTS (10 pt); the plan permits tables down to 8 pt and
        # the sealed tables used the 11 pt body size. Only the FW Table paragraph style changes.
        text = data.decode("utf-8")
        m = re.search(r'<w:style [^>]*w:styleId="FWTable".*?</w:style>', text, re.S)
        if not m:
            raise ValueError("FWTable style not found")
        block = m.group(0)
        new_block = block.replace('<w:sz w:val="22"/><w:szCs w:val="22"/>',
                                  f'<w:sz w:val="{TABLE_FONT_HALF_PTS}"/><w:szCs w:val="{TABLE_FONT_HALF_PTS}"/>')
        if new_block == block:
            raise ValueError("FWTable size run not found")
        return text.replace(block, new_block).encode("utf-8")

    def footnotes(data: bytes) -> bytes:
        old = f"<w:t xml:space=\"preserve\">{FOOTNOTE_1_OLD}</w:t>".encode()
        if data.count(old) != 1:
            raise ValueError("footnote 1 text not found exactly once")
        from xml.sax.saxutils import escape
        data = data.replace(old, f"<w:t xml:space=\"preserve\">{escape(FOOTNOTE_1_NEW)}</w:t>".encode())
        return lib.add_footnotes(data, NEW_FOOTNOTES)

    lib.rewrite_docx_parts(out_path, {"word/footnotes.xml": footnotes,
                                      "word/document.xml": document,
                                      "word/styles.xml": styles,
                                      "word/media/image3.png": lambda _: gantt_bytes})
    return out_path


def validate_docx(out_path: Path) -> list[str]:
    baseline = lib.docx_text(BASELINE_DOCX)
    output = lib.docx_text(out_path)
    text = output.all_text
    failures: list[str] = []
    failures += lib.check_forbidden(output.body, FORBIDDEN)
    failures += lib.check_required(text, REQUIRED)
    failures += lib.check_deliverable_ids(output.body, set(DELIVERABLE_MONTHS))
    failures += lib.check_cut_ledger(CUT_LEDGER, baseline.all_text, text)
    failures += lib.check_effort_model(EFFORT_MATRIX, PERIOD_TOTALS, WP_TOTALS, 30.0)
    for label, passage in PROTECTED:
        if lib.norm(passage) not in lib.norm(text):
            failures.append(f"protected passage altered: {label}")
    headers = lib.extract_wp_headers(output.body)
    if [h[0] for h in headers] != ["WP1", "WP2", "WP3", "WP4", "WP5"]:
        failures.append(f"WP headers: {[h[0] for h in headers]}")
    for wp, _, _, _, pm in headers:
        if abs(pm - WP_TOTALS[wp]) > 0.01:
            failures.append(f"{wp} header PM {pm} != {WP_TOTALS[wp]}")
    if sum(h[4] for h in headers) - 30.0 > 0.01:
        failures.append("WP header PM do not sum to 30.0")
    # deliverable months in §3.1 lines must match the Gantt data
    body = lib.norm(output.body)
    for did, month in DELIVERABLE_MONTHS.items():
        pattern = re.escape(did) + r"[^;]{0,80}?\(M" + str(month) + r"\b"
        if not re.search(pattern, body):
            failures.append(f"{did} not stated at M{month} in the §3.1 deliverable lines")
    for ms, month in MILESTONE_MONTHS.items():
        if f"{ms} (M{month})" not in body:
            failures.append(f"{ms} (M{month}) missing from the decision-gate paragraph")
    if sorted(output.footnotes) != list(range(1, 10)):
        failures.append(f"footnote ids {sorted(output.footnotes)}")
    # Word rejects a document that references one footnote id twice; every footnote is cited once
    import zipfile
    with zipfile.ZipFile(out_path) as z:
        refs = re.findall(r'<w:footnoteReference w:id="(\d+)"', z.read("word/document.xml").decode("utf-8"))
    if sorted(int(r) for r in refs) != list(range(1, 10)):
        failures.append(f"footnote references {refs} must cite ids 1–9 exactly once each")
    used_cuts = [c for e in EDITS for c in e.cuts]
    ledger_ids = {c.cut_id for c in CUT_LEDGER}
    for dup in sorted({c for c in used_cuts if used_cuts.count(c) > 1}):
        failures.append(f"cut {dup} charged to more than one edit")
    for c in sorted(set(used_cuts) - ledger_ids):
        failures.append(f"edit charges unknown cut {c}")
    for c in sorted(ledger_ids - set(used_cuts)):
        failures.append(f"ledger cut {c} not charged to any edit")
    questions = [p for p in output.paragraphs if "?" in p]
    if len(questions) != 1 or "FIELDWISE asks" not in questions[0]:
        failures.append(f"unexpected question marks in {len(questions)} paragraphs")
    return failures


def layout_checks(report: dict) -> list[str]:
    """Layout targets of the plan: §3 on page 8 top, Gantt on page 9, §3.2 on page 10."""
    failures = []
    pages = report["per_page"]
    if len(pages) != 10:
        return ["page count is not 10; layout targets not evaluated"]
    if not pages[7]["first_line"].startswith("3."):
        failures.append(f"page 8 does not start with Section 3: {pages[7]['first_line']!r}")
    if pages[8]["images"] != 1:
        failures.append("Gantt image is not on page 9")
    if not pages[9]["first_line"].startswith("3.2"):
        failures.append(f"page 10 does not start with 3.2: {pages[9]['first_line']!r}")
    return failures


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-export", action="store_true", help="build and validate the DOCX only")
    parser.add_argument("--render-dir", type=Path, default=None, help="where page PNGs are written")
    parser.add_argument("--report", action="store_true", help="write the refactoring report")
    args = parser.parse_args(argv)

    out = build_docx()
    failures = validate_docx(out)
    for f in failures:
        print(f"[FAIL] {f}")
    print(f"[ok] built {out.relative_to(REPO)} ({len(EDITS)} edits, {len(CUT_LEDGER)} cuts)")
    if args.no_export:
        return 1 if failures else 0

    pages = lib.export_pdf_with_word(out, OUT_PDF)
    report = lib.pdf_report(OUT_PDF, expected_pages=10,
                            placeholders=["[OWNER-CONFIRM", "[TBC]", "TODO", "[Page limit]"])
    layout = layout_checks(report)
    for p in report["per_page"]:
        print(f"  p{p['page']:02d} slack={p['slack_lines']:>4} lines  body {p['min_body_pt']}pt "
              f"other {p['min_other_pt']}pt  L{p['left_margin_mm']} R{p['right_margin_mm']}mm  "
              f"imgs={p['images']}  {p['footer']}  | {p['first_line'][:60]}")
    for f in report["failures"] + layout:
        print(f"[FAIL] {f}")
    print(f"[info] Word page count {pages}; PDF pages {report['pages']}")
    if args.render_dir:
        paths = lib.render_pages(OUT_PDF, args.render_dir, "refactored")
        print(f"[ok] rendered {len(paths)} pages to {args.render_dir}")
    if args.report:
        from tools.partb1_refactor_report import write_report  # noqa: E402

        write_report(REPORT_MD, EDITS, CUT_LEDGER, IN_PLACE_COMPRESSIONS, PROTECTED, failures,
                     report, layout)
        print(f"[ok] report {REPORT_MD.relative_to(REPO)}")
    return 1 if (failures or report["failures"] or layout) else 0


if __name__ == "__main__":
    sys.exit(main())
