# -*- coding: utf-8 -*-
import json, io

nodes, edges = [], []

def N(**kw): nodes.append(kw)
def E(s, t, ty, w): edges.append({"source": s, "target": t, "type": ty, "direction": "forward", "weight": w})

HM = "document:harness/HARNESS.md"
SC_RIA = "config:harness/evaluator_scorecard_ria.json"
SC_PF = "config:harness/evaluator_scorecard_msca_pf.json"
SC_PF_MD = "document:harness/evaluator_scorecard_msca_pf.md"
RB_RIA = "config:harness/rubrics_ria.json"
RB_PF = "config:harness/rubrics_msca_pf.json"

N(id=HM, type="document", name="HARNESS.md", filePath="harness/HARNESS.md",
  summary="Specification document for the out-of-band evaluation and integrity harness, defining its substrate (E1/E1.5), the two headline signals E2 (status-aware faithfulness) and E3 (claim-ledger completeness plus status calibration), the E4 regression golden-set, the pre-evaluation profile layer and the blind-assessment lane. It is the authority for the harness's load-bearing invariant: no eval metric may wire into the runtime DAG as a fail-closed gate.",
  tags=["documentation", "specification", "evaluation-harness", "quality-assurance", "entry-point"],
  complexity="complex",
  languageNotes="Documents a structurally enforced one-way import boundary (harness depends on runner, never the reverse), asserted by tests/harness/test_boundary.py rather than by prose alone.")

N(id=SC_RIA, type="config", name="evaluator_scorecard_ria.json", filePath="harness/evaluator_scorecard_ria.json",
  summary="Machine-readable RIA/IA evaluator scorecard transcribed from the EU Grants Evaluation form (HE RIA and IA) V4.0, pp.4-5: the 0-5 scoring scale with its level descriptions, the three criteria (Excellence, Impact, Implementation) each carrying a threshold score of 3, and the six verbatim aspect texts the harness grades against.",
  tags=["configuration", "scorecard", "ria", "evaluation-criteria", "schema-definition"],
  complexity="moderate",
  languageNotes="An RIA form is single-type and unweighted, so option_tag and weight_pct are declared Inferred rather than transcribed, recorded as Milestone 1 defects F1 and F2.")

N(id=SC_PF, type="config", name="evaluator_scorecard_msca_pf.json", filePath="harness/evaluator_scorecard_msca_pf.json",
  summary="Machine-readable MSCA Postdoctoral Fellowship evaluator scorecard transcribed from the HE MSCA Evaluation Form V2.2, pp.4-6: the 0-5 scale, the 50/30/20 criterion weighting against a 70/100 overall pass threshold, the nine PF-scoped aspects, and the COFUND-only recruiting-institution aspect explicitly excluded from grading.",
  tags=["configuration", "scorecard", "msca-pf", "evaluation-criteria", "schema-definition"],
  complexity="moderate")

N(id=SC_PF_MD, type="document", name="evaluator_scorecard_msca_pf.md", filePath="harness/evaluator_scorecard_msca_pf.md",
  summary="Human-readable mirror of the MSCA-PF evaluator scorecard, listing every criterion, weight and aspect text with its form page and option tag, plus the PF scoping rule that decides which registry aspects are graded and which are excluded.",
  tags=["documentation", "scorecard", "msca-pf", "evaluation-criteria", "reference"],
  complexity="simple",
  languageNotes="Declared a mirror by design: the rubric lane loads the JSON, while this file exists for human verification against the official PDF form.")

N(id=RB_RIA, type="config", name="rubrics_ria.json", filePath="harness/rubrics_ria.json",
  summary="RIA rubric set (ria_ia_rubrics v1.0.0) binding each of the six scorecard aspects to an integrity-framed grading rubric with evaluation steps, a 0.6 pass threshold, selection terms and the Part B sub-section anchors (B.1.1 through B.3.2) that Phase 8 writes.",
  tags=["configuration", "rubric", "ria", "scoring", "evaluation-harness"],
  complexity="moderate",
  languageNotes="Integrity-framed by design: a rubric asks whether a section addresses and grounds its expectation, never whether the prose reads well.")

N(id=RB_PF, type="config", name="rubrics_msca_pf.json", filePath="harness/rubrics_msca_pf.json",
  summary="MSCA-PF rubric set (msca_pf_rubrics v1.0.0) binding each of the nine PF-scoped scorecard aspects to an integrity-framed grading rubric with evaluation steps, a 0.6 pass threshold, selection terms and the sub-section anchors 1.1 through 3.2.",
  tags=["configuration", "rubric", "msca-pf", "scoring", "evaluation-harness"],
  complexity="moderate")

INSTR = {"harness/rubrics_ria.json": ("ria", RB_RIA),
         "harness/rubrics_msca_pf.json": ("msca-pf", RB_PF)}
for path, (tag, parent) in INSTR.items():
    d = json.load(io.open(path, encoding="utf-8"))
    for r in d["rubrics"]:
        key = r["expectation_key"]
        crit = r["criterion_id"]
        anchors = ", ".join(r["anchor_sub_section_ids"])
        txt = " ".join(r["expectation_text"].split())
        if len(txt) > 150:
            txt = txt[:150].rsplit(" ", 1)[0] + "..."
        nid = "config:%s:%s" % (path, key)
        N(id=nid, type="config", name=key, filePath=path,
          summary="Integrity rubric for the %s aspect: %s Graded against sub-section anchor %s with a pass threshold of %s." % (crit, txt, anchors, r["pass_threshold"]),
          tags=["rubric", crit, tag, "scoring", "expectation"],
          complexity="simple")
        E(parent, nid, "contains", 1.0)

SC = {"harness/evaluator_scorecard_ria.json": ("ria", SC_RIA),
      "harness/evaluator_scorecard_msca_pf.json": ("msca-pf", SC_PF)}
for path, (tag, parent) in SC.items():
    d = json.load(io.open(path, encoding="utf-8"))
    for c in d["criteria"]:
        cid = c["id"]
        aspects = ", ".join(a["id"] for a in c["aspects"])
        thr = c.get("threshold_score")
        thr_s = (" Individual threshold score %s." % thr) if thr is not None else ""
        w = c["weight_pct"]
        w_s = ("weight %s%%" % w) if w > 1 else "unweighted, weight_pct carrying the placeholder value 1"
        nid = "config:%s:%s" % (path, cid)
        N(id=nid, type="config", name=cid, filePath=path,
          summary="Scorecard criterion %s (%s, %s, form page %s) covering the aspects %s.%s" % (
              c["name"], c["score_field"], w_s, c["source_page"], aspects, thr_s),
          tags=["scorecard", "criterion", cid, tag, "evaluation-criteria"],
          complexity="simple")
        E(parent, nid, "contains", 1.0)

MODULES = ["verdict.py", "provenance.py", "judge.py", "routing.py", "report.py", "rubric.py",
           "rubrics.py", "expectations.py", "profile.py", "blind_assessment.py", "calibration.py",
           "claim_ledger.py", "faithfulness.py", "gold_set.py", "materiality.py", "regression.py",
           "status_calibration.py", "commands/blind_assessment.py", "commands/rubric_grading_run.py"]
for m in MODULES:
    E(HM, "file:harness/%s" % m, "documents", 0.5)

for t in (SC_RIA, SC_PF, RB_RIA, RB_PF):
    E(HM, t, "documents", 0.5)

E(SC_PF_MD, SC_PF, "documents", 0.5)

RUBRIC_CONSUMERS = ["harness/rubrics.py", "harness/rubric.py",
                    "harness/commands/rubric_grading_run.py", "harness/blind_assessment.py"]
SCORECARD_CONSUMERS = ["harness/profile.py", "harness/rubrics.py",
                       "harness/expectations.py", "harness/rubric.py"]
for src in (RB_RIA, RB_PF):
    for c in RUBRIC_CONSUMERS:
        E(src, "file:%s" % c, "configures", 0.6)
for src in (SC_RIA, SC_PF):
    for c in SCORECARD_CONSUMERS:
        E(src, "file:%s" % c, "configures", 0.6)

E(RB_RIA, RB_PF, "related", 0.5)
E(SC_RIA, SC_PF, "related", 0.5)

ids = [n["id"] for n in nodes]
assert len(ids) == len(set(ids)), "duplicate node ids"
for e in edges:
    assert e["source"] != e["target"], "self edge"
assert len({(e["source"], e["target"], e["type"]) for e in edges}) == len(edges), "duplicate edge"

out = "C:/Code/proposal_demo/proposal_orchestrator/.ua/intermediate/batch-10.json"
with io.open(out, "w", encoding="utf-8") as f:
    f.write(json.dumps({"nodes": nodes, "edges": edges}, indent=1, ensure_ascii=False))
print("nodes", len(nodes), "edges", len(edges))
