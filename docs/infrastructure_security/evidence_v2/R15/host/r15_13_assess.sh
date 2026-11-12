#!/usr/bin/env bash
# R15 step 13 (evidence_v2/R15/STEPS.md): runbook step 12, converse_smoke assess through the launcher.
# The only step that calls a model. Its log, the blind report, the checkpoint, the baseline and the
# receipt stay on the host and go with it at step 14 (point 6). Prints metadata only: the exit code,
# the receipt check lines, the report count, the checkpoint's line count, and the name, size and
# sha256 of each baseline file. Then reads the receipt again with check.
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root, 3,600 s timeout, point 7).
# The last line is RESULT=expected or RESULT=unexpected.
set -u
export HOME="${HOME:-/root}"
umask 077
W=/root/r15
APP=/opt/msca-dn-anonymisation/app
PY=/opt/msca-dn-anonymisation/python/bin/python3
ROOT="$W/converse"
RECEIPT="$W/readiness_receipt.json"
LAUNCH="--region eu-north-1 --secret-id proposal-orchestrator/env-config"
echo "CHECK=r15-13-assess"
if ! cd "$APP" 2>/dev/null || [ ! -x "$PY" ] || [ ! -f "$RECEIPT" ]; then
  echo "receipt=absent"
  echo "RESULT=unexpected"
  exit 0
fi
echo "start_utc=$(date -u +%FT%TZ)"
# shellcheck disable=SC2086
"$PY" -m runner.host_env $LAUNCH -- \
  "$PY" -m harness.commands.converse_smoke assess --root "$ROOT" --receipt "$RECEIPT" \
  >"$W/13_assess.log" 2>"$W/13_assess.err"
rc=$?
echo "end_utc=$(date -u +%FT%TZ)"
echo "assess_exit=$rc"
# The lines after "frozen into" are the receipt check lines and the verdict, never report text.
sed -n '/^frozen into /,$p' "$W/13_assess.log" | tail -n +2 | while IFS= read -r line; do
  echo "assess_line=$line"
done
# A refusal names its reason and, before the pass, the receipt check lines.
grep -E '^(refused:|  |host_env)' "$W/13_assess.err" | head -n 20 | while IFS= read -r line; do
  echo "refused_line=$line"
done
reports=$(find "$ROOT/world/reports" -maxdepth 1 -type f -name '*.json' 2>/dev/null | wc -l)
echo "report_count=$reports"
checkpoint=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["checkpoint"])' "$ROOT/prepared.json" 2>/dev/null)
if [ -n "$checkpoint" ] && [ -f "$checkpoint" ]; then
  echo "checkpoint_lines=$(wc -l <"$checkpoint")"
else
  echo "checkpoint_lines=absent"
fi
baseline=0
if [ -d "$ROOT/baseline" ]; then
  find "$ROOT/baseline" -type f | sort >"$W/13_baseline.list"
  while IFS= read -r f; do
    baseline=$((baseline + 1))
    echo "baseline_file=${f#"$ROOT/baseline/"} size=$(stat -c %s "$f") sha256=$(sha256sum "$f" | cut -d' ' -f1)"
  done <"$W/13_baseline.list"
fi
echo "baseline_files=$baseline"
echo "receipt_sha256=$(sha256sum "$RECEIPT" | cut -d' ' -f1)"
# shellcheck disable=SC2086
"$PY" -m runner.host_env $LAUNCH -- \
  "$PY" -m harness.commands.converse_smoke check --root "$ROOT" --receipt "$RECEIPT" \
  >"$W/13_check.out" 2>"$W/13_check.err"
check=$?
echo "check_exit=$check"
while IFS= read -r line; do echo "check_line=$line"; done <"$W/13_check.out"
first_err=$(head -n 1 "$W/13_check.err")
[ -z "$first_err" ] || echo "stderr_first=$first_err"
if [ "$rc" -eq 0 ] && [ "$reports" -eq 1 ] && [ "$baseline" -ge 1 ] && [ "$check" -eq 0 ] \
  && [ "$(tail -n 1 "$W/13_check.out")" = "receipt green" ]; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
