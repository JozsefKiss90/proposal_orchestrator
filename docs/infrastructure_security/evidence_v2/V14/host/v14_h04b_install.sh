#!/usr/bin/env bash
# V14 step h04b (evidence_v2/V14/STEPS.md; R15 step 08's script, working directory /root/v14): extract the bundle into /tmp and run its install_host.sh
# (runbook plans/msca_dn_an12_host_runbook.md step 6). Sent alone by deploy/aws/scripts/host-run.ps1
# (Run Command, as root). Prints key=value lines only; the last is RESULT=expected or RESULT=unexpected.
# The install log stays in /root/v14 on the host.
set -u
export HOME="${HOME:-/root}"
umask 022
W=/root/v14
TAR=msca-dn-anonymisation-host.tar.gz
TARGET=/opt/msca-dn-anonymisation
LOG="$W/08_install.log"
echo "CHECK=v14-h04b-install"
if ! cd "$W" 2>/dev/null || [ ! -f "$W/$TAR" ]; then
  echo "tarball=absent"
  echo "RESULT=unexpected"
  exit 0
fi
tar xzf "$W/$TAR" -C /tmp >"$W/08_tar.log" 2>&1
tar_rc=$?
echo "tar_exit=$tar_rc"
bash /tmp/msca-dn-anonymisation-host/app/deploy/install_host.sh "$TARGET" >"$LOG" 2>&1
rc=$?
echo "install_exit=$rc"
sums_ok=$(grep -c ': OK$' "$LOG")
sums_failed=$(grep -Ec ': FAILED' "$LOG")
py_version=$(grep -m 1 '^Python 3' "$LOG")
detail=$(sed -n '/^=== Verifying the installed files ===$/{n;p;}' "$LOG")
echo "sums_ok=$sums_ok"
echo "sums_failed=$sums_failed"
echo "python_version=${py_version:-none}"
echo "files_detail=${detail:-none}"
refused=$(grep -m 1 '^refused:' "$LOG")
[ -z "$refused" ] || echo "refused=$refused"
if grep -q 'INSTALL_COMPLETE' "$LOG"; then complete=yes; else complete=no; fi
echo "install_complete=$complete"
echo "installed_kb=$(du -sk "$TARGET" 2>/dev/null | cut -f1)"
echo "free_root_kb=$(df -Pk / | awk 'NR==2 {print $4}')"
if [ "$tar_rc" -eq 0 ] && [ "$rc" -eq 0 ] && [ "$sums_failed" = "0" ] && [ "$py_version" = "Python 3.11.16" ] \
  && [ "$detail" = "all 299 files match the manifest" ] && [ "$complete" = "yes" ]; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
