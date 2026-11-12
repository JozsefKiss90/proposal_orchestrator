#!/usr/bin/env bash
# V14 step H05a (evidence_v2/V14/STEPS.md): runbook §5's preflight on the host, then the receipt draft
# of runbook §1.1. No model call. Every command runs with --repo-root /root/v14/R (REHEARSAL.md R5) and
# the two budgets of V14-F7. The draft is built as harness.commands.converse_smoke builds R15's: the
# request comes from the judge's own Converse builder, which makes no network call.
# Writes /root/v14/prepared.json (the exact assess and freeze lines) and /root/v14/receipt_draft.json.
# Prints key=value lines only: exit codes, the pack set, flag categories (never a flag's text), the
# rendered request's five fields and the placeholders left. The last is RESULT=expected or unexpected.
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root).
# V14_W, V14_APP, V14_PY and V14_LAUNCH=none override the host for the workstation rehearsal only. V14_EXPECT_PACK_SET
# likewise: the synthetic rehearsal root has its own pack set.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${V14_W:-/root/v14}"
R="$W/R"
APP="${V14_APP:-/opt/msca-dn-anonymisation/app}"
PY="${V14_PY:-/opt/msca-dn-anonymisation/python/bin/python3}"
MODEL=eu.anthropic.claude-sonnet-4-6
VERSION="bedrock-converse-eu-north-1@$(date -u +%F)"
EXPECT_PACK_SET="${V14_EXPECT_PACK_SET:-sha256:fe975e4b8489}"
run() {
  if [ "${V14_LAUNCH:-host_env}" = none ]; then "$@"
  else "$PY" -m runner.host_env --region eu-north-1 --secret-id proposal-orchestrator/env-config -- "$@"; fi
}
echo "CHECK=v14-h05a-prepare"
if ! cd "$APP" 2>/dev/null || [ ! -x "$PY" ] || [ ! -d "$R" ]; then
  echo "install_or_root=absent"
  echo "RESULT=unexpected"
  exit 0
fi
if [ -e "$W/prepared.json" ] || [ -e "$R/reports_preflight" ]; then
  echo "prepared=exists"
  echo "RESULT=unexpected"
  exit 0
fi
cat >"$W/v14_prepare.py" <<'PYEOF'
import contextlib, json, os, re, sys
from pathlib import Path
app, root, work, model, version, expect_pack = sys.argv[1:7]
sys.path.insert(0, app)
os.chdir(app)
import harness.commands.blind_assessment as ba
import harness.commands.converse_smoke as cs
from harness.record_binding import file_sha256
DOC = "MSCA-DN-2025_part_b_as_submitted"
PROFILE = "harness/profiles/msca_dn_2025_historical.json"
root, work = Path(root), Path(work)
def say(k, v):
    print(f"{k}={v}", flush=True)
manifests = sorted(p for p in root.rglob("docs/tier4_orchestration_state/dev_graph/imports/*.json")
                   if p.is_file())
say("import_manifests", len(manifests))
if len(manifests) != 1:
    say("RESULT_PY", "unexpected"); sys.exit(0)
manifest = manifests[0]
graph = manifest.parents[4]
shared = ["--repo-root", str(root), "--document", DOC, "--graph-root", str(graph), "--profile", PROFILE,
          "--transport", "bedrock-converse", "--no-claims", "--grounding-scope", "content_focused",
          "--package-budget", "400000", "--criterion-budget", "40000", "--import-manifest", str(manifest)]
pf_dir = root / "reports_preflight"
with open(work / "h05a_preflight.log", "w", encoding="utf-8") as log, contextlib.redirect_stdout(log), \
        contextlib.redirect_stderr(log):
    rc = ba.main(["preflight", *shared, "--out-dir", str(pf_dir)])
say("preflight_exit", rc)
found = sorted(pf_dir.glob("preflight_*.json"))
say("preflight_reports", len(found))
if rc not in (0, 1) or len(found) != 1:
    say("RESULT_PY", "unexpected"); sys.exit(0)
pf_path = found[0]
pf = json.loads(pf_path.read_text(encoding="utf-8"))
pack = str(pf.get("pack_set_hash") or "")
say("pack_set", pack[:19])
say("pack_set_matches_w07", "yes" if pack.startswith(expect_pack) else "no")
flags = list(pf.get("flags") or [])
say("flags", len(flags))
for i, flag in enumerate(flags):
    head = str(flag).split(":", 1)[0].strip()
    say(f"flag_{i}_category", head if re.fullmatch(r"[A-Za-z][A-Za-z _-]{0,30}", head) else "other")
package = pf.get("package") if isinstance(pf.get("package"), dict) else {}
say("package_completeness", package.get("completeness"))
say("package_budget", package.get("budget"))
say("packs", len(pf.get("packs") or []))
checkpoint = root / ".harness" / "checkpoints" / "v14_stage_a.jsonl"
say("checkpoint_exists", "yes" if checkpoint.exists() else "no")
assess = ["assess", *shared, "--preflight", str(pf_path), "--intake", "msca-dn-2025-original",
          "--assessor-model", model, "--assessor-version", version,
          "--out-dir", str(root / "reports"), "--checkpoint", str(checkpoint)]
args = ba._parser().parse_args(assess)
judge = ba._live_judge(args, root)
request = judge._backend._inner._build_request([{"role": "user", "content": ""}])
sent = request["inferenceConfig"]
region = os.environ.get("AWS_REGION", "")
doc = json.loads(cs.TEMPLATE.read_text(encoding="utf-8"))
doc.pop("_what_this_is")
revision = json.loads(cs.BUNDLE_MANIFEST.read_text(encoding="utf-8"))["repository_revision"]
doc.update(receipt_id="v14_stage_a_original", private_clone_root=str(root), repository_revision=revision)
doc["model_identity"]["pin"] = cs.blind.assessor_pin(judge)
values = {"model": request["modelId"], "temperature": str(sent["temperature"]),
          "max_tokens": str(sent["maxTokens"])}
for setting in doc["effective_settings"]:
    setting["value"] = values[setting["name"]]
doc["rendered_request"].update(model_id=request["modelId"], temperature=sent["temperature"],
                               max_tokens=sent["maxTokens"], tool_config_present="toolConfig" in request,
                               region=region)
doc["checkpoint"]["path"] = str(checkpoint)
pm = pf["import_manifest"]
doc["preflight"] = {
    "report_path": str(pf_path), "report_sha256": file_sha256(pf_path),
    "pack_set_hash": pf["pack_set_hash"], "document_id": pf["document_id"],
    "profile_id": pf["profile_id"], "profile_path": str(Path(app) / PROFILE),
    "profile_sha256": file_sha256(Path(app) / PROFILE), "profile_version": pf["profile_version"],
    "import_manifest_path": pm["path"], "import_manifest_sha256": pm["sha256"],
    "grounding_scope": cs.gs.declared_scope_of(pf),
}
draft = work / "receipt_draft.json"
fd = os.open(draft, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
prepared = {"document": DOC, "profile": PROFILE, "root": str(root), "graph_root": str(graph),
            "import_manifest": str(manifest), "preflight": str(pf_path), "checkpoint": str(checkpoint),
            "assessor_model": model, "assessor_version": version, "assess_argv": assess}
fd = os.open(work / "prepared.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    json.dump(prepared, handle, indent=2)
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
EXPECTED = {
    "authored_on", "review_state", "declared_status", "purpose", "written_by",
    "processing_route.authority", "processing_route.processing", "processing_route.export",
    "processing_route.verified_on", "processing_route.verified_by",
    "isolation_check.evidence[0]", "isolation_check.verified_on", "isolation_check.verified_by",
}
left = sorted(holes(doc))
req = doc["rendered_request"]
say("assessor_version", version)
say("repository_revision", revision)
say("model_pin", doc["model_identity"]["pin"])
for key in ("model_id", "temperature", "max_tokens", "tool_config_present", "region"):
    say(f"rendered_request.{key}", json.dumps(req.get(key)))
say("placeholders", ",".join(left))
say("draft_sha256", file_sha256(draft))
ok = (pack.startswith(expect_pack) and revision == "17e32d54f2bd60c1d69d9a1b6caa8688c34f036e"
      and doc["model_identity"]["pin"] == f"{model}@{version}" and req.get("model_id") == model
      and req.get("temperature") == 0 and req.get("tool_config_present") is False
      and req.get("region") == "eu-north-1" and set(left) == EXPECTED and not checkpoint.exists()
      and package.get("completeness") == "complete")
say("RESULT_PY", "expected" if ok else "unexpected")
PYEOF
out=$(run "$PY" "$W/v14_prepare.py" "$APP" "$R" "$W" "$MODEL" "$VERSION" "$EXPECT_PACK_SET" 2>"$W/h05a_prepare.err")
rc=$?
printf '%s\n' "$out" | grep -v '^RESULT_PY='
echo "prepare_exit=$rc"
first_err=$(grep -m 1 -E "^(refused|host_env|Traceback|[A-Za-z]+Error)" "$W/h05a_prepare.err" | cut -c1-200)
[ -z "$first_err" ] || echo "stderr_first=$first_err"
if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -qx 'RESULT_PY=expected'; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
