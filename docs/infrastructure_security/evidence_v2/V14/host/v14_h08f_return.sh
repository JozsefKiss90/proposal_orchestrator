#!/usr/bin/env bash
# V14 step H08f-r (evidence_v2/V14/STEPS.md): what returns from the private diagnosis record (DIAGNOSIS.md, "What
# returns to the repository", confirmed by the operator 2026-11-13). Reads
# /root/v14/R/private/msca_dn_original/esr_work/diagnosis_private.json, written by "v14_diag.py finalize" in the
# interactive session. It does not write or re-finalize anything.
# Prints the record's path, size, mode and sha256; its bindings, each checked against the file it names; the
# counts block and comparison_by_disposition, each key checked against a fixed vocabulary; and totals derived from
# them. No observation id, no note, no text: a key outside the vocabulary is refused, not printed.
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root). The last line is RESULT=expected or
# RESULT=unexpected. V14_W and V14_PY override the host for the workstation rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${V14_W:-/root/v14}"
PY="${V14_PY:-/opt/msca-dn-anonymisation/python/bin/python3}"
echo "CHECK=v14-h08f-return"
if [ ! -d "$W/R" ] || [ ! -x "$PY" ]; then
  echo "root=absent"
  echo "RESULT=unexpected"
  exit 0
fi
out=$("$PY" - "$W/R" <<'PYEOF'
import hashlib, json, os, re, sys
from pathlib import Path
root = Path(sys.argv[1])
def say(k, v):
    print(f"{k}={v}", flush=True)
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def stop(reason):
    say("refused", reason); say("RESULT", "unexpected"); sys.exit(0)
CATS = ("evidence_omission", "extraction", "rubric_interpretation", "assessor_error",
        "historical_subjectivity", "unresolved_cause")
STATUSES = ("Confirmed", "Inferred", "Assumed", "Unresolved")
WHO = ("operator", "rule")
ANSWERS = ("yes", "no", "unclear")
DISPOSITIONS = ("independently_detected", "partially_observable", "not_assessable_from_this_copy",
                "not_detected_despite_sufficient_preserved_evidence", "addressed")
ALLOWED = set()
for cls in ("misses", "false_positives", "deltas"):
    ALLOWED |= {f"{cls}.category.{c}" for c in CATS}
    ALLOWED |= {f"{cls}.status.{s}" for s in STATUSES}
    ALLOWED |= {f"{cls}.decided_by.{w}" for w in WHO}
for cls in ("contested", "AVC-01", "AVC-02"):
    ALLOWED |= {f"{cls}.answer.{a}" for a in ANSWERS}
    ALLOWED |= {f"{cls}.decided_by.{w}" for w in WHO}
rel = "private/msca_dn_original/esr_work/diagnosis_private.json"
rec_p = root / rel
if not rec_p.is_file():
    stop("diagnosis_private.json is not there: run finalize in the session first")
say("record", rel)
say("record_size", rec_p.stat().st_size)
say("record_mode", oct(rec_p.stat().st_mode & 0o777)[2:])
say("record_sha256", sha(rec_p))
rec = json.loads(rec_p.read_text(encoding="utf-8"))
say("record_type", rec.get("record_type"))
say("schema_version", rec.get("schema_version"))
say("written_utc", rec.get("written_utc"))
if rec.get("record_type") != "v14_private_diagnosis":
    stop("not a v14_private_diagnosis record")
b = rec.get("bindings") or {}
ok = True
for name in ("report", "comparison"):
    p = str(b.get(name) or "")
    if not re.fullmatch(r"(baseline|comparisons)/[A-Za-z0-9_.]+\.json", p):
        stop(f"the {name} binding is not a plain path under baseline/ or comparisons/")
    f = root / p
    match = f.is_file() and sha(f) == b.get(f"{name}_sha256")
    ok = ok and match
    say(f"binding.{name}", p)
    say(f"binding.{name}_sha256", b.get(f"{name}_sha256"))
    say(f"binding.{name}_matches_file", "yes" if match else "no")
comps = sorted((root / "comparisons").glob("comparison_*_[0-9][0-9][0-9][0-9].json"))
latest = f"comparisons/{comps[-1].name}" if comps else ""
say("latest_comparison", latest)
say("binding_is_latest_comparison", "yes" if b.get("comparison") == latest else "no")
cnt = rec.get("counts") or {}
bad = [k for k in cnt if k not in ALLOWED or not isinstance(cnt[k], int) or isinstance(cnt[k], bool)]
if bad:
    stop(f"{len(bad)} count key(s) outside the vocabulary; none printed")
for k in sorted(cnt):
    say(f"count.{k}", cnt[k])
bd = rec.get("comparison_by_disposition") or {}
if set(bd) - set(DISPOSITIONS) or not all(isinstance(v, int) for v in bd.values()):
    stop("comparison_by_disposition holds a key or value outside the vocabulary")
for k in DISPOSITIONS:
    say(f"comparison_by_disposition.{k}", bd.get(k, 0))
comp_p = root / str(b.get("comparison") or "")
if comp_p.is_file():
    live = (json.loads(comp_p.read_text(encoding="utf-8")).get("summary") or {}).get("by_disposition") or {}
    say("comparison_by_disposition_equals_file", "yes" if {k: live.get(k) for k in DISPOSITIONS} == {k: bd.get(k, 0) for k in DISPOSITIONS} else "no")
def total(prefix):
    return sum(v for k, v in cnt.items() if k.startswith(prefix))
for cls in ("misses", "false_positives", "deltas"):
    say(f"total.{cls}", total(f"{cls}.category."))
for cls in ("contested", "AVC-01", "AVC-02"):
    say(f"total.{cls}", total(f"{cls}.answer."))
say("total.decided_by_rule", sum(v for k, v in cnt.items() if k.endswith(".decided_by.rule")))
say("misses_equal_not_detected", "yes" if total("misses.category.") == bd.get(DISPOSITIONS[3], -1) else "no")
say("RESULT", "expected" if ok else "unexpected")
PYEOF
)
rc=$?
printf '%s\n' "$out"
echo "driver_exit=$rc"
printf '%s\n' "$out" | grep -qx 'RESULT=expected' || { printf '%s\n' "$out" | grep -q '^RESULT=' || echo "RESULT=unexpected"; }
exit 0
