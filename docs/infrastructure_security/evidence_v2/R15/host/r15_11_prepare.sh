#!/usr/bin/env bash
# R15 step 11 (evidence_v2/R15/STEPS.md): runbook step 11, converse_smoke prepare through the launcher.
# Builds the synthetic world under /root/r15/converse and drafts the receipt. No model call.
# Assessor and tag are point 10's. Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root).
# Prints key=value lines only: the draft's sha256, revision, pin, the rendered request's five fields and
# the placeholders left. The last line is RESULT=expected or RESULT=unexpected.
set -u
export HOME="${HOME:-/root}"
umask 077
W=/root/r15
APP=/opt/msca-dn-anonymisation/app
PY=/opt/msca-dn-anonymisation/python/bin/python3
ROOT="$W/converse"
MODEL=eu.anthropic.claude-sonnet-4-6
VERSION="bedrock-converse-eu-north-1@$(date -u +%F)"
echo "CHECK=r15-11-prepare"
if ! cd "$APP" 2>/dev/null || [ ! -x "$PY" ]; then
  echo "install=absent"
  echo "RESULT=unexpected"
  exit 0
fi
if [ -e "$ROOT" ]; then
  echo "converse_root=exists"
  echo "RESULT=unexpected"
  exit 0
fi
"$PY" -m runner.host_env --region eu-north-1 --secret-id proposal-orchestrator/env-config -- \
  "$PY" -m harness.commands.converse_smoke prepare --root "$ROOT" \
  --assessor-model "$MODEL" --assessor-version "$VERSION" >"$W/11_prepare.log" 2>&1
rc=$?
echo "prepare_exit=$rc"
echo "assessor_version=$VERSION"
if [ "$rc" -ne 0 ]; then
  line=$(grep -m 1 -E '^(refused:|host_env)' "$W/11_prepare.log")
  [ -z "$line" ] || echo "refused=$line"
fi
out=$("$PY" - "$ROOT/receipt_draft.json" "$MODEL" "$VERSION" <<'PYEOF'
import hashlib, json, re, sys
path, model, version = sys.argv[1:4]
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
try:
    raw = open(path, "rb").read()
    doc = json.loads(raw)
except (OSError, ValueError):
    print("draft=absent")
    sys.exit(0)
req = doc.get("rendered_request", {})
found = sorted(holes(doc))
print("draft_sha256=" + hashlib.sha256(raw).hexdigest())
print("repository_revision=" + str(doc.get("repository_revision")))
print("model_pin=" + str(doc.get("model_identity", {}).get("pin")))
for key in ("model_id", "temperature", "max_tokens", "tool_config_present", "region"):
    print(f"rendered_request.{key}={json.dumps(req.get(key))}")
print("placeholders=" + ",".join(found))
ok = (doc.get("repository_revision") == "17e32d54f2bd60c1d69d9a1b6caa8688c34f036e"
      and doc.get("model_identity", {}).get("pin") == f"{model}@{version}"
      and req.get("model_id") == model and req.get("temperature") == 0
      and req.get("tool_config_present") is False and req.get("region") == "eu-north-1"
      and set(found) == EXPECTED)
print("draft_as_expected=" + ("yes" if ok else "no"))
PYEOF
)
printf '%s\n' "$out"
if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -qx 'draft_as_expected=yes'; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
