#!/usr/bin/env bash
# R15 step 12 (evidence_v2/R15/STEPS.md): fill the receipt with point 5's values and read it (V13).
# Copies the draft to /root/r15/readiness_receipt.json (mode 600), outside every checkout (ticket 13),
# fills exactly the thirteen operator fields, then runs converse_smoke check through the launcher.
# No model call. Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root). Prints
# key=value lines only; the last is RESULT=expected or RESULT=unexpected.
# The filler between FILL markers is run by tests/test_aws_host_run_script.py against a real draft.
set -u
export HOME="${HOME:-/root}"
umask 077
W=/root/r15
APP=/opt/msca-dn-anonymisation/app
PY=/opt/msca-dn-anonymisation/python/bin/python3
ROOT="$W/converse"
RECEIPT="$W/readiness_receipt.json"
echo "CHECK=r15-12-receipt"
if ! cd "$APP" 2>/dev/null || [ ! -x "$PY" ] || [ ! -f "$ROOT/receipt_draft.json" ]; then
  echo "draft=absent"
  echo "RESULT=unexpected"
  exit 0
fi
if [ -e "$RECEIPT" ]; then
  echo "receipt=exists"
  echo "RESULT=unexpected"
  exit 0
fi
"$PY" - "$ROOT/receipt_draft.json" "$RECEIPT" "$(date -u +%F)" <<'FILL'
import json, os, re, sys
draft, out, day = sys.argv[1:4]
EXPECTED = {
    "authored_on", "review_state", "declared_status", "purpose", "written_by",
    "processing_route.authority", "processing_route.processing", "processing_route.export",
    "processing_route.verified_on", "processing_route.verified_by",
    "isolation_check.evidence[0]", "isolation_check.verified_on", "isolation_check.verified_by",
}
HOLE = re.compile(r"<[^>]*>")
def holes(node, at=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from holes(v, f"{at}.{k}" if at else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from holes(v, f"{at}[{i}]")
    elif isinstance(node, str) and HOLE.search(node):
        yield at
doc = json.load(open(draft, encoding="utf-8"))
found = set(holes(doc))
if found != EXPECTED:
    print("fill_refused=placeholders differ: " + ",".join(sorted(found ^ EXPECTED)))
    sys.exit(1)
doc.update(
    authored_on=day,
    review_state="operator_reviewed",
    declared_status="Confirmed",
    purpose="R15 (AN12 criterion 3): the synthetic Converse blind pass on the private host",
    written_by="the operator, from values drafted by the agent in evidence_v2/R15/STEPS.md "
               "and approved in session",
)
doc["processing_route"].update(
    authority="ADR-001 for the new account (OD1-r1 eu-north-1, OD7 model set) and AN0 O6 "
              "(msca-dn-anonymisation-operator-decisions_2026-10-14): the harness blind assessor "
              "may call Bedrock Converse",
    processing="the synthetic dev-graph world only (tests/fixtures/dev_graph_synthetic); "
               "no proposal text",
    export="metadata only: exit codes, receipt check lines, file names, sizes and sha256 values; "
           "no model output leaves the host",
    verified_on=day,
    verified_by="the operator",
)
doc["isolation_check"].update(
    evidence=[
        "tests/harness/test_converse_judge.py::TestTheJudgeBuildsConverse",
        "tests/harness/test_converse_smoke.py",
        "the rendered request in receipt_draft.json: tool_config_present false (step 11)",
    ],
    verified_on=day,
    verified_by="the operator",
)
left = sorted(holes(doc))
fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
print("placeholders_left=" + (",".join(left) or "none"))
sys.exit(1 if left else 0)
FILL
fill=$?
echo "fill_exit=$fill"
echo "receipt_sha256=$(sha256sum "$RECEIPT" 2>/dev/null | cut -d' ' -f1)"
echo "receipt_mode=$(stat -c %a "$RECEIPT" 2>/dev/null)"
"$PY" -m runner.host_env --region eu-north-1 --secret-id proposal-orchestrator/env-config -- \
  "$PY" -m harness.commands.converse_smoke check --root "$ROOT" --receipt "$RECEIPT" \
  >"$W/12_check.out" 2>"$W/12_check.err"
check=$?
echo "check_exit=$check"
while IFS= read -r line; do echo "check_line=$line"; done <"$W/12_check.out"
first_err=$(head -n 1 "$W/12_check.err")
[ -z "$first_err" ] || echo "stderr_first=$first_err"
if [ "$fill" -eq 0 ] && [ "$check" -eq 0 ] && [ "$(tail -n 1 "$W/12_check.out")" = "receipt green" ]; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
