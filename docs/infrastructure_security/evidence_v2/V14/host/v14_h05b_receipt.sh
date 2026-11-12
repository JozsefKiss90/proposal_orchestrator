#!/usr/bin/env bash
# V14 step H05b (evidence_v2/V14/STEPS.md): fill the receipt's thirteen operator fields with the values
# of STEPS.md point P2, then validate it as runbook §1.1 says, before the run. No model call.
# The receipt is /root/v14/readiness_receipt.json (mode 600), outside the private root and outside the
# installed checkout (ticket 13). Prints key=value lines only; the validator's lines name paths, hashes
# and rule names, never proposal text. The last line is RESULT=expected or RESULT=unexpected.
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root).
# V14_W, V14_APP, V14_PY and V14_LAUNCH=none override the host for the workstation rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${V14_W:-/root/v14}"
APP="${V14_APP:-/opt/msca-dn-anonymisation/app}"
PY="${V14_PY:-/opt/msca-dn-anonymisation/python/bin/python3}"
DRAFT="$W/receipt_draft.json"
RECEIPT="$W/readiness_receipt.json"
run() {
  if [ "${V14_LAUNCH:-host_env}" = none ]; then "$@"
  else "$PY" -m runner.host_env --region eu-north-1 --secret-id proposal-orchestrator/env-config -- "$@"; fi
}
echo "CHECK=v14-h05b-receipt"
if ! cd "$APP" 2>/dev/null || [ ! -x "$PY" ] || [ ! -f "$DRAFT" ]; then
  echo "draft=absent"
  echo "RESULT=unexpected"
  exit 0
fi
if [ -e "$RECEIPT" ]; then
  echo "receipt=exists"
  echo "RESULT=unexpected"
  exit 0
fi
"$PY" - "$DRAFT" "$RECEIPT" "$(date -u +%F)" <<'FILL'
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
    purpose="V14 Stage A (plans/msca_dn_historical_validation_tickets.md): the blind assessment of the "
            "MSCA-DN 2025 original over Bedrock Converse on the private host, historical profile",
    written_by="the operator, from values drafted by the agent in evidence_v2/V14/STEPS.md "
               "and approved in session",
)
doc["processing_route"].update(
    authority="ADR-001 for the new account (OD1-r1 eu-north-1, OD7 model set); AN0 O6 "
              "(msca-dn-anonymisation-operator-decisions_2026-10-14), which approves the Converse "
              "transport for the harness blind assessor; and the operator's V14 decisions "
              "V14-OP1 to V14-OP9 (evidence_v2/V14/RUNLOG.md), which send the original to it",
    processing="the MSCA-DN 2025 original's Part B (a page extract of the portal PDF, declared "
               "Inferred), as packed in input-20261112-40eb1f.tar.gz: evidence packs and criterion "
               "inputs under the historical profile; no Part A",
    export="metadata, numeric scores and spreads only (V14-OP2); finding text, quotes, dispositions "
           "and declarations stay on the host",
    verified_on=day,
    verified_by="the operator",
)
doc["isolation_check"].update(
    evidence=[
        "tests/harness/test_converse_judge.py::TestTheJudgeBuildsConverse",
        "tests/harness/test_converse_judge.py::TestTheInvocationRecordIsMeasured",
        "the rendered request in receipt_draft.json: tool_config_present false (step H05a)",
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
run "$PY" -m harness.commands.execution_receipt --receipt "$RECEIPT" \
  --expect-candidate MSCA-DN-2025_part_b_as_submitted \
  --expect-profile harness/profiles/msca_dn_2025_historical.json \
  >"$W/h05b_check.out" 2>"$W/h05b_check.err"
check=$?
echo "check_exit=$check"
while IFS= read -r line; do echo "check_line=$line"; done <"$W/h05b_check.out"
first_err=$(head -n 1 "$W/h05b_check.err" | cut -c1-200)
[ -z "$first_err" ] || echo "stderr_first=$first_err"
if [ "$fill" -eq 0 ] && [ "$check" -eq 0 ]; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
