#!/usr/bin/env bash
# V14 steps H08b and H08e-3 (evidence_v2/V14/STEPS.md): runbook §6's audit, after the freeze and after the ESR
# record is in place. --repo-root the private root and --package-budget 400000 (V14-F7); the import
# manifest named as the candidate provenance. No model call. The audit report stays on the host.
# PO_AUDIT_LABEL names the run (first | successor); each writes into its own directory.
# Prints key=value lines only: the exit code (1 when the audit flags, which is advisory), the flag
# count, and the report's name, size and sha256. The last is RESULT=expected or RESULT=unexpected.
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root).
# V14_W, V14_APP, V14_PY and V14_LAUNCH=none override the host for the workstation rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${V14_W:-/root/v14}"
APP="${V14_APP:-/opt/msca-dn-anonymisation/app}"
PY="${V14_PY:-/opt/msca-dn-anonymisation/python/bin/python3}"
LABEL="${PO_AUDIT_LABEL:-}"
run() {
  if [ "${V14_LAUNCH:-host_env}" = none ]; then "$@"
  else "$PY" -m runner.host_env --region eu-north-1 --secret-id proposal-orchestrator/env-config -- "$@"; fi
}
echo "CHECK=v14-h08-audit"
echo "label=$LABEL"
case "$LABEL" in first|successor) ;; *) echo "refused=PO_AUDIT_LABEL must be first or successor"; echo "RESULT=unexpected"; exit 0 ;; esac
if ! cd "$APP" 2>/dev/null || [ ! -x "$PY" ] || [ ! -f "$W/prepared.json" ]; then
  echo "prepared=absent"
  echo "RESULT=unexpected"
  exit 0
fi
cat >"$W/v14_audit.py" <<'PYEOF'
import contextlib, hashlib, json, os, sys
from pathlib import Path
app, work, label = sys.argv[1:4]
sys.path.insert(0, app)
os.chdir(app)
import harness.commands.blind_assessment as ba
work = Path(work)
def say(k, v):
    print(f"{k}={v}", flush=True)
prep = json.loads((work / "prepared.json").read_text(encoding="utf-8"))
root = Path(prep["root"])
esr = root / "docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-original-esr.json"
say("esr_present", "yes" if esr.is_file() else "no")
baseline = root / "baseline"
say("baseline_present", "yes" if baseline.is_dir() else "no")
out_dir = root / "audit" / label
if out_dir.exists() or not esr.is_file() or not baseline.is_dir():
    say("audit_dir_before", "exists" if out_dir.exists() else "absent")
    say("RESULT_PY", "unexpected"); sys.exit(0)
argv = ["audit", "--repo-root", str(root), "--document", prep["document"], "--graph-root", prep["graph_root"],
        "--profile", prep["profile"], "--package-budget", "400000",
        "--candidate-provenance", prep["import_manifest"], "--baseline-dir", str(baseline),
        "--out-dir", str(out_dir)]
with open(work / f"h08_audit_{label}.log", "w", encoding="utf-8") as log, contextlib.redirect_stdout(log), \
        contextlib.redirect_stderr(log):
    rc = ba.main(argv)
say("audit_exit", rc)
found = sorted(p for p in out_dir.glob("*.json")) if out_dir.is_dir() else []
say("audit_reports", len(found))
for p in found:
    say("audit_file", f"audit/{label}/{p.name} size={p.stat().st_size} "
                      f"sha256={hashlib.sha256(p.read_bytes()).hexdigest()}")
    doc = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(doc, dict):
        say("audit_flags", len(doc.get("flags") or []))
        bound = doc.get("baseline") if isinstance(doc.get("baseline"), dict) else {}
        say("baseline_bound", bound.get("bound", bound.get("status", "unknown")))
ok = rc in (0, 1) and len(found) == 1
say("RESULT_PY", "expected" if ok else "unexpected")
PYEOF
out=$(run "$PY" "$W/v14_audit.py" "$APP" "$W" "$LABEL" 2>"$W/h08_audit.err")
rc=$?
printf '%s\n' "$out" | grep -v '^RESULT_PY='
echo "driver_exit=$rc"
first_err=$(grep -m 1 -E "^(refused|host_env|Traceback|[A-Za-z]+Error)" "$W/h08_audit.err" | cut -c1-200)
[ -z "$first_err" ] || echo "stderr_first=$first_err"
if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -qx 'RESULT_PY=expected'; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
