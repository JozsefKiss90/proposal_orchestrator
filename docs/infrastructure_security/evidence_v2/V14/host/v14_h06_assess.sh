#!/usr/bin/env bash
# V14 step H06 (evidence_v2/V14/STEPS.md): runbook section 5's assessment and freeze, the only model step.
# Reads the receipt first and refuses unless it is green; runs the exact assess line H05a recorded in
# /root/v14/prepared.json (both V14-F7 budgets, --repo-root the private root); freezes; then reads the
# receipt again against the report (runbook section 1.1). With PO_RESUME=yes the same line runs with
# --resume in place of --checkpoint, on the same checkpoint path, and nothing else changes (V14-D2).
# The assess log, the report, the checkpoint, the provenance log and the baseline stay on the host.
# Prints metadata only: exit codes, call counts, the name, size and sha256 of each baseline file, the
# freeze's condition count, and the receipt check lines. The last is RESULT=expected or unexpected.
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root, 7,200 s timeout).
# V14_W, V14_APP, V14_PY and V14_LAUNCH=none override the host for the workstation rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${V14_W:-/root/v14}"
APP="${V14_APP:-/opt/msca-dn-anonymisation/app}"
PY="${V14_PY:-/opt/msca-dn-anonymisation/python/bin/python3}"
RESUME="${PO_RESUME:-no}"
run() {
  if [ "${V14_LAUNCH:-host_env}" = none ]; then "$@"
  else "$PY" -m runner.host_env --region eu-north-1 --secret-id proposal-orchestrator/env-config -- "$@"; fi
}
echo "CHECK=v14-h06-assess"
echo "resume=$RESUME"
if ! cd "$APP" 2>/dev/null || [ ! -x "$PY" ] || [ ! -f "$W/prepared.json" ] || [ ! -f "$W/readiness_receipt.json" ]; then
  echo "prepared_or_receipt=absent"
  echo "RESULT=unexpected"
  exit 0
fi
cat >"$W/v14_assess.py" <<'PYEOF'
import contextlib, hashlib, json, os, sys
from pathlib import Path
app, work, resume = sys.argv[1:4]
sys.path.insert(0, app)
os.chdir(app)
import harness.commands.blind_assessment as ba
import harness.commands.execution_receipt as erc
work = Path(work)
def say(k, v):
    print(f"{k}={v}", flush=True)
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
prep = json.loads((work / "prepared.json").read_text(encoding="utf-8"))
root = Path(prep["root"])
receipt = str(work / "readiness_receipt.json")
check_args = ["--receipt", receipt, "--expect-candidate", prep["document"], "--expect-profile", prep["profile"]]
def receipt_check(tag, extra):
    with open(work / f"h06_{tag}.out", "w", encoding="utf-8") as out, contextlib.redirect_stdout(out):
        rc = erc.main([*check_args, *extra])
    say(f"receipt_{tag}_exit", rc)
    for line in (work / f"h06_{tag}.out").read_text(encoding="utf-8").splitlines():
        say(f"receipt_{tag}_line", line)
    return rc
reports = root / "reports"
before = sorted(reports.glob("blind_*.json")) if reports.is_dir() else []
say("reports_before", len(before))
if before:
    say("RESULT_PY", "unexpected"); sys.exit(0)
checkpoint = Path(prep["checkpoint"])
say("checkpoint_before", "present" if checkpoint.exists() else "absent")
if resume == "yes" and not checkpoint.exists():
    say("RESULT_PY", "unexpected"); sys.exit(0)
if resume != "yes" and checkpoint.exists():
    say("RESULT_PY", "unexpected"); sys.exit(0)
if receipt_check("before", []) != 0:
    say("RESULT_PY", "unexpected"); sys.exit(0)
argv = list(prep["assess_argv"])
if resume == "yes":
    argv[argv.index("--checkpoint")] = "--resume"
say("assess_argv_sha256", hashlib.sha256(json.dumps(argv).encode()).hexdigest()[:16])
say("assess_start_utc", __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
log_name = "h06_assess_resume.log" if resume == "yes" else "h06_assess.log"
with open(work / log_name, "w", encoding="utf-8") as log, contextlib.redirect_stdout(log), \
        contextlib.redirect_stderr(log):
    try:
        rc = ba.main(argv)
    except Exception as exc:  # the type only; the message stays in the log on the host
        print(repr(exc))
        rc = "exception:" + type(exc).__name__
say("assess_end_utc", __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
say("assess_exit", rc)
found = sorted(reports.glob("blind_*.json")) if reports.is_dir() else []
say("report_count", len(found))
cands = sorted(p for p in (reports / "candidates").iterdir()) if (reports / "candidates").is_dir() else []
say("candidate_count", len(cands))
say("checkpoint_lines", sum(1 for _ in checkpoint.open(encoding="utf-8")) if checkpoint.exists() else "absent")
if rc != 0 or len(found) != 1 or len(cands) != 1:
    say("RESULT_PY", "unexpected"); sys.exit(0)
report_path = found[0]
report = json.loads(report_path.read_text(encoding="utf-8"))
inv = report.get("assessor_invocation") or {}
say("report_file", report_path.name)
say("report_sha256", sha(report_path))
for key in ("live_calls", "replayed_calls", "discarded_draws"):
    say(key, report.get(key))
say("requests", inv.get("requests"))
say("tool_config_sent", inv.get("tool_config_sent"))
say("child_process", inv.get("child_process"))
say("inference_config", json.dumps(inv.get("inference_config"), sort_keys=True))
scoring = report.get("criterion_scoring") or {}
say("unscored_criteria", len(scoring.get("unscored_criteria") or []))
baseline = root / "baseline"
freeze = ["freeze", "--repo-root", str(root), "--report", str(report_path), "--candidate", str(cands[0]),
          "--profile", prep["profile"], "--baseline-dir", str(baseline)]
with open(work / "h06_freeze.log", "w", encoding="utf-8") as log, contextlib.redirect_stdout(log), \
        contextlib.redirect_stderr(log):
    frc = ba.main(freeze)
say("freeze_exit", frc)
files = sorted(p for p in baseline.rglob("*") if p.is_file()) if baseline.is_dir() else []
for p in files:
    say("baseline_file", f"{p.relative_to(baseline).as_posix()} size={p.stat().st_size} sha256={sha(p)}")
say("baseline_files", len(files))
passed = None
for p in files:
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        continue
    if isinstance(doc, dict) and isinstance(doc.get("checks_passed"), list):
        passed = len(doc["checks_passed"])
say("freeze_checks_passed", passed)
after = receipt_check("after", ["--report", str(report_path)])
ok = frc == 0 and passed == 22 and after == 0 and not scoring.get("unscored_criteria")
say("RESULT_PY", "expected" if ok else "unexpected")
PYEOF
out=$(run "$PY" "$W/v14_assess.py" "$APP" "$W" "$RESUME" 2>"$W/h06_assess.err")
rc=$?
printf '%s\n' "$out" | grep -v '^RESULT_PY='
echo "driver_exit=$rc"
first_err=$(grep -m 1 -E "^(refused|host_env|Traceback|[A-Za-z]+Error)" "$W/h06_assess.err" | cut -c1-200)
[ -z "$first_err" ] || echo "stderr_first=$first_err"
if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -qx 'RESULT_PY=expected'; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
