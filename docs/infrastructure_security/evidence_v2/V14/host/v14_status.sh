#!/usr/bin/env bash
# V14 status (evidence_v2/V14/STEPS.md H08d): what the private root holds after the
# interactive section 6 work, as metadata. For each file under the run's output directories and the operator's
# dispositions and notes, it prints the root-relative path, the size and the sha256. Never content.
# Run it after each interactive sitting, so the evidence shows which comparison, review and diff
# files exist and that none moved afterwards.
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root). The last line is RESULT=expected
# when the private root exists. V14_W overrides /root/v14 for the workstation rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${V14_W:-/root/v14}"
R="$W/R"
echo "CHECK=v14-status"
if [ ! -d "$R" ]; then
  echo "root=absent"
  echo "RESULT=unexpected"
  exit 0
fi
echo "root_mode=$(stat -c %a "$R")"
total=0
for d in reports_preflight reports baseline audit comparisons reviews diffs private/msca_dn_original/esr_work .harness/checkpoints; do
  n=0
  if [ -d "$R/$d" ]; then
    while IFS= read -r f; do
      n=$((n + 1))
      echo "file=${f#"$R/"} size=$(stat -c %s "$f") sha256=$(sha256sum "$f" | cut -d' ' -f1)"
    done < <(find "$R/$d" -type f | sort)
  fi
  echo "count_${d//[\/.]/_}=$n"
  total=$((total + n))
done
for f in "$R"/private/*/fidelity_register_*.json; do
  [ -f "$f" ] && echo "register=${f#"$R/"} size=$(stat -c %s "$f") sha256=$(sha256sum "$f" | cut -d' ' -f1)"
done
echo "files_listed=$total"
echo "RESULT=expected"
exit 0
