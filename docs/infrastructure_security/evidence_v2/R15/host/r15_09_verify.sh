#!/usr/bin/env bash
# R15 step 09 (evidence_v2/R15/STEPS.md): runbook step 7, offline_bundle verify through the launcher
# under the production configuration. Probe pypi.org:443; if that name does not resolve, the route was
# not measured (AN12 R8), and the probe reruns against 1.1.1.1:443 (point 9).
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root). Prints key=value lines and the
# verification record, whole; the last line is RESULT=expected or RESULT=unexpected.
set -u
export HOME="${HOME:-/root}"
umask 077
W=/root/r15
APP=/opt/msca-dn-anonymisation/app
PY=/opt/msca-dn-anonymisation/python/bin/python3
REC="$W/verification.json"
echo "CHECK=r15-09-verify"
if ! cd "$APP" 2>/dev/null || [ ! -x "$PY" ]; then
  echo "install=absent"
  echo "RESULT=unexpected"
  exit 0
fi
verify() {
  rm -f "$REC"
  "$PY" -m runner.host_env --region eu-north-1 --secret-id proposal-orchestrator/env-config -- \
    "$PY" -m runner.offline_bundle verify --probe-no-internet "$1" --record "$REC" \
    >"$W/09_verify.out" 2>"$W/09_verify.err"
}
unresolved() {
  "$PY" - "$REC" <<'PYEOF'
import json, sys
try:
    record = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError):
    sys.exit(1)
route = [c for c in record.get("checks", []) if c.get("check") == "no_internet_route"]
sys.exit(0 if route and "did not resolve" in str(route[0].get("detail", "")) else 1)
PYEOF
}
probe=pypi.org:443
verify "$probe"
rc=$?
if unresolved; then
  echo "probe_unresolved=$probe"
  probe=1.1.1.1:443
  verify "$probe"
  rc=$?
fi
echo "verify_probe=$probe"
echo "verify_exit=$rc"
first_err=$(head -n 1 "$W/09_verify.err")
[ -z "$first_err" ] || echo "stderr_first=$first_err"
"$PY" - "$REC" <<'PYEOF'
import json, sys
try:
    record = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError):
    print("record=absent")
    sys.exit(0)
print("record_passed=" + str(record.get("passed")).lower())
for c in record.get("checks", []):
    print(f"check_{c.get('check')}={str(c.get('passed')).lower()}")
print("record=" + json.dumps(record, sort_keys=True, separators=(",", ":")))
PYEOF
passed=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["passed"] is True)' "$REC" 2>/dev/null)
if [ "$rc" -eq 0 ] && [ "$passed" = "True" ]; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
