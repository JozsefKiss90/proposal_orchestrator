#!/usr/bin/env bash
# V14 step H09 (evidence_v2/V14/STEPS.md): what returns to the repository, by whitelist (V14-OP2).
# Reads the one blind report under /root/v14/R/reports and prints, as key=value lines, only numbers,
# booleans, hashes and identifiers named below: the run's binding and call counts, each cell's score,
# agreement and sample scores, and each criterion's score, spread, sample scores and weighting.
# No rationale, strength, shortcoming, quote, finding text, disposition or declaration is read out:
# a string value is printed only from the named identifier fields, and only if it matches
# [A-Za-z0-9_.:@/+-]{1,120}; otherwise the line says "withheld".
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root). The last line is
# RESULT=expected or RESULT=unexpected. V14_W and V14_PY override the host for the rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${V14_W:-/root/v14}"
R="$W/R"
PY="${V14_PY:-/opt/msca-dn-anonymisation/python/bin/python3}"
echo "CHECK=v14-h09-return"
if [ ! -x "$PY" ] || [ ! -d "$R/reports" ]; then
  echo "reports=absent"
  echo "RESULT=unexpected"
  exit 0
fi
out=$("$PY" - "$R/reports" <<'PYEOF'
import hashlib, json, re, sys
from pathlib import Path
SAFE = re.compile(r"[A-Za-z0-9_.:@/+-]{1,120}")
def say(k, v):
    print(f"{k}={v}")
def ident(v):
    if v is None or isinstance(v, bool):
        return json.dumps(v)
    if isinstance(v, str):
        return v if SAFE.fullmatch(v) else "withheld"
    return "withheld"
def num(v):
    if v is None or isinstance(v, bool) or isinstance(v, (int, float)):
        return json.dumps(v)
    return "withheld"
found = sorted(Path(sys.argv[1]).glob("blind_*.json"))
say("reports", len(found))
if len(found) != 1:
    say("RESULT", "unexpected"); sys.exit(0)
p = found[0]
r = json.loads(p.read_text(encoding="utf-8"))
say("report_file", ident(p.name))
say("report_sha256", hashlib.sha256(p.read_bytes()).hexdigest())
for k in ("record_type", "metric", "candidate_hash", "profile_id", "profile_version", "assessor_pin",
          "assessor_transport", "scope", "rubric_set_id", "rubric_set_version", "scorecard_id",
          "scorecard_version", "intake_id", "snapshot_id", "package_id", "preflight_pack_set_hash",
          "assessed_at", "esr_availability", "evidence_view", "evidence_source"):
    say(k, ident(r.get(k)))
for k in ("include_claims", "live_calls", "replayed_calls", "discarded_draws", "advisory", "blocking"):
    say(k, num(r.get(k)))
say("partial_coverage_count", len(r.get("partial_coverage") or []))
inv = r.get("assessor_invocation") or {}
for k in ("tool_config_sent", "child_process", "requests"):
    say(f"invocation.{k}", num(inv.get(k)))
for k, v in sorted((inv.get("inference_config") or {}).items()):
    say(f"invocation.inference_config.{ident(k)}", num(v))
gsc = r.get("grounding_scope") or {}
for k in ("declared", "measured"):
    say(f"grounding_scope.{k}", ident(gsc.get(k)))
s = r.get("summary") or {}
for k in ("cells", "covered", "clean_pass", "missing_sections"):
    say(f"summary.{k}", num(s.get(k)))
for cid, c in sorted((s.get("criteria") or {}).items()):
    for k in ("cells", "covered", "clean_pass", "mean_score"):
        say(f"summary.criteria.{ident(cid)}.{k}", num(c.get(k)))
for i, c in enumerate(r.get("cells") or []):
    cov = c.get("coverage") or {}
    ver = cov.get("verdict") or {}
    members = [num(m.get("score")) for m in ver.get("members") or []]
    say(f"cell_{i}", " ".join([
        f"criterion={ident(c.get('criterion_id'))}", f"expectation={ident(c.get('expectation_key'))}",
        f"section={ident(c.get('section_id'))}", f"covered={num(c.get('covered'))}",
        f"addressal={num(c.get('addressal'))}", f"clean_pass={num(c.get('clean_pass'))}",
        f"score={num(c.get('score'))}", f"agreement={num(ver.get('agreement'))}", f"n={num(ver.get('n'))}",
        f"pack_status={ident(cov.get('pack_status'))}", f"pack_tokens={num(cov.get('pack_token_estimate'))}",
        f"member_scores={','.join(members)}", f"discarded={len(c.get('discarded_draws') or [])}"]))
cs = r.get("criterion_scoring") or {}
for k in ("total", "overall_threshold", "overall_max", "overall_threshold_met", "individual_threshold",
          "individual_thresholds_met", "samples_per_criterion", "scale_max", "score_resolution"):
    say(f"criterion_scoring.{k}", num(cs.get(k)))
say("criterion_scoring.failing_criteria", ",".join(ident(x) for x in cs.get("failing_criteria") or []) or "none")
say("criterion_scoring.unscored_criteria", ",".join(ident(x) for x in cs.get("unscored_criteria") or []) or "none")
for sc in cs.get("scores") or []:
    cid = ident(sc.get("criterion_id"))
    inp = sc.get("input") or {}
    samples = [num(x.get("score")) for x in sc.get("samples") or []]
    say(f"criterion.{cid}", " ".join([
        f"status={ident(sc.get('status'))}", f"score={num(sc.get('score'))}", f"spread={num(sc.get('spread'))}",
        f"sample_scores={','.join(samples)}",
        f"threshold={num(sc.get('threshold'))}", f"threshold_met={num(sc.get('threshold_met'))}",
        f"weight={num(sc.get('weight'))}", f"factor={num(sc.get('factor'))}",
        f"weighted_points={num(sc.get('weighted_points'))}", f"input_tokens={num(inp.get('token_estimate'))}",
        f"input_budget={num(inp.get('token_budget'))}", f"input_complete={num(inp.get('complete'))}",
        f"discarded={len(sc.get('discarded_draws') or [])}"]))
say("RESULT", "expected")
PYEOF
)
printf '%s\n' "$out"
printf '%s\n' "$out" | grep -q '^RESULT=' || echo "RESULT=unexpected"
exit 0
