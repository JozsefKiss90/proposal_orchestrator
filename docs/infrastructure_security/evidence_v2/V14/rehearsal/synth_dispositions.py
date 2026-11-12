"""Write a synthetic schema-1.2 dispositions file for the rehearsal root.

usage: synth_dispositions.py <root> <out rel> <mode: inferred|confirmed> [<supersedes rel>]
Reads only ids from the ESR record; every free-text field is a fixed synthetic string.
"""
import hashlib
import json
import sys
from pathlib import Path

root, out_rel, mode = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
sup = sys.argv[4] if len(sys.argv) > 4 else None
sha = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()  # noqa: E731
first = lambda pattern: next(p for p in sorted(root.glob(pattern))).relative_to(root).as_posix()  # noqa: E731

ESR = "docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-original-esr.json"
REG = "private/msca_dn_original/fidelity_register_as_submitted.json"
report = first("reports/blind_*.json")
cand = first("reports/candidates/*")
audit = sorted((root / "audit").glob("integrity_*.json"))[-1].relative_to(root).as_posix()
ids = [o["id"] for o in json.loads((root / ESR).read_text(encoding="utf-8-sig"))["observations"]]
MISS = ids[2]

rows = []
for i in ids:
    if i != MISS:
        rows.append({"observation_id": i, "disposition": "not_assessable_from_this_copy",
                     "declared_status": "Assumed", "evidence_basis": ["derived/sub_sections/1.1"],
                     "explanation": "Synthetic rehearsal row.", "review_status": "operator_decision_required"})
        continue
    row = {"observation_id": i, "disposition": "not_detected_despite_sufficient_preserved_evidence",
           "declared_status": "Inferred",
           "current_evidence": [{"section_id": "excellence_section", "sub_section_id": "1.1",
                                 "quote": "Nine beneficiaries host the candidates across four countries."}],
           "explanation": "Synthetic rehearsal miss.", "review_status": "operator_decision_required",
           "failure_mode": "absent_from_recorded_output",
           "failure_mode_basis": "Synthetic: the assessor's recorded output does not name it."}
    if mode == "confirmed":
        row["evidence_preserved_status"] = "Confirmed"
        row["evidence_basis"] = ["derived/sub_sections/1.1",
                                 "declared/sub_sections/1.1/fidelity_to_submitted_original"]
    else:
        row["evidence_preserved_status"] = "Inferred"
        row["evidence_basis"] = ["derived/sub_sections/1.1"]
    rows.append(row)

doc = {
    "record_type": "esr_dispositions", "schema_version": "1.2",
    "advisory": True, "blocking": False, "review_state": "agent_drafted_pending_operator_review",
    "baseline_report_sha256": json.loads((root / report).read_text(encoding="utf-8-sig")).get("report_sha256")
    or hashlib.sha256((root / report).read_bytes()).hexdigest(),
    "baseline_dir": "baseline",
    "esr_record": ESR, "esr_record_sha256": sha(ESR),
    "candidate": cand,
    "fidelity_register": REG, "fidelity_register_sha256": sha(REG),
    "audits": [audit],
    "declared_by": "rehearsal", "declared_on": "2026-11-12",
    "rows": rows,
}
if sup:
    doc["supersedes"] = sup
    doc["supersedes_sha256"] = sha(sup)
(root / out_rel).parent.mkdir(parents=True, exist_ok=True)
(root / out_rel).write_text(json.dumps(doc, indent=2), encoding="utf-8")
print(f"wrote {out_rel} rows={len(rows)} miss={MISS} mode={mode}")
