#!/usr/bin/env bash
# V14 step H08c-0 (evidence_v2/V14/STEPS.md): build the skeleton of the first dispositions record before the
# interactive sitting. Schema 1.2. One row per observation id of the approved template
# (dispositions_f60ae6e0a2a1_approved.json), in its order; the ids must equal the ESR record's, in the same order.
# The header is bound to the ESR record on the host (the successor record, sha256 5c9b9c8e...) and to the frozen
# baseline of H06 (the freeze record's report_sha256). Every judgement field is left empty: disposition,
# declared_status and explanation are "", blind_findings is [], declared_by and declared_on are "". No text of the
# template is copied: only its ids. compare refuses the skeleton until the operator fills it (V14-OP4).
# Writes /root/v14/R/private/msca_dn_original/esr_work/dispositions_first.json (mode 600), refusing if it exists.
# Prints key=value lines only: paths, counts, hashes and identifiers. No model call, no AWS call.
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root). The last line is RESULT=expected or
# RESULT=unexpected. V14_W, V14_APP and V14_PY override the host for the workstation rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${V14_W:-/root/v14}"
APP="${V14_APP:-/opt/msca-dn-anonymisation/app}"
PY="${V14_PY:-/opt/msca-dn-anonymisation/python/bin/python3}"
echo "CHECK=v14-h08c-skeleton"
if ! cd "$APP" 2>/dev/null || [ ! -x "$PY" ] || [ ! -d "$W/R" ]; then
  echo "root=absent"
  echo "RESULT=unexpected"
  exit 0
fi
out=$("$PY" - "$APP" "$W/R" <<'PYEOF'
import hashlib, json, os, sys
from pathlib import Path
app, root = sys.argv[1], Path(sys.argv[2])
sys.path.insert(0, app)
def say(k, v):
    print(f"{k}={v}", flush=True)
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def stop(reason):
    say("refused", reason); say("RESULT", "unexpected"); sys.exit(0)
ESR_DIR = "docs/tier4_orchestration_state/msca_dn/esr"
esr_rel = f"{ESR_DIR}/msca-dn-2025-original-esr.json"
tpl_rel = f"{ESR_DIR}/dispositions_f60ae6e0a2a1_approved.json"
out_rel = "private/msca_dn_original/esr_work/dispositions_first.json"
esr, tpl, out = root / esr_rel, root / tpl_rel, root / out_rel
say("esr_present", "yes" if esr.is_file() else "no")
say("template_present", "yes" if tpl.is_file() else "no")
if not esr.is_file() or not tpl.is_file():
    stop("the ESR record or the approved template is not under the root")
if out.exists():
    stop("dispositions_first.json exists")
t = json.loads(tpl.read_text(encoding="utf-8-sig"))
e = json.loads(esr.read_text(encoding="utf-8-sig"))
say("template_sha256", sha(tpl))
say("template_schema_version", t.get("schema_version"))
ids = [r.get("observation_id") for r in t.get("rows") or []]
esr_ids = [str(o.get("id")) for o in e.get("observations") or []]
say("template_rows", len(ids))
say("esr_sha256", sha(esr))
say("esr_observations", len(esr_ids))
say("ids_equal_esr_in_order", "yes" if ids == esr_ids else "no")
if t.get("record_type") != "esr_dispositions" or t.get("schema_version") != "1.2":
    stop("the template is not an esr_dispositions record of schema 1.2")
if len(ids) != 29 or len(set(ids)) != 29 or not all(isinstance(i, str) for i in ids):
    stop("the template does not hold 29 distinct observation ids")
if ids != esr_ids:
    stop("the template's ids are not the ESR record's, in order")
freezes = sorted((root / "baseline").glob("*.freeze.json"))
say("freeze_records", len(freezes))
if len(freezes) != 1:
    stop("not exactly one freeze record under baseline/")
fr = json.loads(freezes[0].read_text(encoding="utf-8-sig"))
report_sha = str(fr.get("report_sha256") or "")
copies = [p for p in (root / "baseline").glob("*.json") if not p.name.endswith(".freeze.json")]
copy_ok = len(copies) == 1 and sha(copies[0]) == report_sha
say("freeze_record", f"baseline/{freezes[0].name}")
say("baseline_report_sha256", report_sha)
say("baseline_copy_matches", "yes" if copy_ok else "no")
if not copy_ok:
    stop("the baseline copy does not hash to the freeze record's report_sha256")
doc = {
    "record_type": "esr_dispositions",
    "schema_version": "1.2",
    "artifact_purpose": "V14 Stage A: the operator's first dispositions of the original's ESR observations "
                        "against the frozen blind baseline (runbook section 6, route iii)",
    "written_by": "skeleton by evidence_v2/V14/host/v14_h08c_skeleton.sh; every judgement field by the operator",
    "baseline_report_sha256": report_sha,
    "baseline_dir": "baseline",
    "esr_record": esr_rel,
    "esr_record_sha256": sha(esr),
    "template": tpl_rel,
    "template_sha256": sha(tpl),
    "template_note": "observation ids only, in the template's order; no disposition, status, explanation or "
                     "finding of the template is carried over",
    "declared_by": "",
    "declared_on": "",
    "rows": [{"observation_id": i, "disposition": "", "declared_status": "", "explanation": "",
              "blind_findings": []} for i in ids],
}
out.parent.mkdir(parents=True, exist_ok=True)
os.chmod(out.parent, 0o700)
fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
from harness.esr_comparison import load_dispositions
loaded = load_dispositions(out)
say("skeleton", out_rel)
say("skeleton_sha256", loaded.sha256)
say("skeleton_mode", oct(out.stat().st_mode & 0o777)[2:])
say("skeleton_rows", len(loaded.rows))
say("skeleton_loads", "yes")
say("first_id", ids[0])
say("last_id", ids[-1])
say("empty_fields", "declared_by,declared_on,rows[].disposition,rows[].declared_status,rows[].explanation,rows[].blind_findings")
say("RESULT", "expected")
PYEOF
)
rc=$?
printf '%s\n' "$out"
echo "driver_exit=$rc"
printf '%s\n' "$out" | grep -qx 'RESULT=expected' || { printf '%s\n' "$out" | grep -q '^RESULT=' || echo "RESULT=unexpected"; }
exit 0
