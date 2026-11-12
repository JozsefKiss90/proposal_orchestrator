#!/usr/bin/env bash
# V14 step h04a (evidence_v2/V14/STEPS.md; R15 step 07's script, working directory /root/v14): fetch the O5 bundle from the deploy bucket and check its sha256.
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root). Prints key=value lines only;
# the last is RESULT=expected or RESULT=unexpected. Logs stay in /root/v14 on the host.
# The bucket is DeployBucketName of R7_outputs.json; the hash and size are O5's
# (decision record msca-dn-refreeze-o5_2026-11-12).
set -u
export HOME="${HOME:-/root}"
umask 077
W=/root/v14
SRC=s3://proposal-orchestrator-deploy-797661577394/bundles/msca-dn-freeze-2026-11-12
TAR=msca-dn-anonymisation-host.tar.gz
EXPECT_SHA=9c5351ef709905c391fd82d06ccdacf1a806c255350241c6d88a21b4d0f2132a
EXPECT_SIZE=92413570
echo "CHECK=v14-h04a-fetch"
if ! mkdir -p "$W" || ! cd "$W"; then
  echo "workdir=unusable"
  echo "RESULT=unexpected"
  exit 0
fi
if ! command -v aws >/dev/null 2>&1; then
  echo "aws_cli=absent"
  echo "RESULT=unexpected"
  exit 0
fi
echo "aws_cli=$(aws --version 2>&1 | cut -d' ' -f1)"
aws s3 cp "$SRC/$TAR" "$W/$TAR" --region eu-north-1 --only-show-errors >"$W/07_cp_tar.log" 2>&1
cp_tar=$?
echo "cp_tar_exit=$cp_tar"
[ "$cp_tar" -eq 0 ] || echo "cp_tar_error=$(grep -o '([A-Za-z]*)' "$W/07_cp_tar.log" | head -n 1 | tr -d '()')"
aws s3 cp "$SRC/$TAR.sha256" "$W/$TAR.sha256" --region eu-north-1 --only-show-errors >"$W/07_cp_sha.log" 2>&1
cp_sha=$?
echo "cp_sha_exit=$cp_sha"
[ "$cp_sha" -eq 0 ] || echo "cp_sha_error=$(grep -o '([A-Za-z]*)' "$W/07_cp_sha.log" | head -n 1 | tr -d '()')"
size=$(stat -c %s "$W/$TAR" 2>/dev/null || echo absent)
sha=$(sha256sum "$W/$TAR" 2>/dev/null | cut -d' ' -f1)
check=$(sha256sum -c "$TAR.sha256" 2>/dev/null | sed -n "s/^$TAR: //p")
echo "size=$size"
echo "sha256=${sha:-absent}"
echo "sha256sum_check=${check:-none}"
echo "free_root_kb=$(df -Pk / | awk 'NR==2 {print $4}')"
echo "free_tmp_kb=$(df -Pk /tmp | awk 'NR==2 {print $4}')"
echo "tmp_fstype=$(df -PT /tmp | awk 'NR==2 {print $2}')"
if [ "$cp_tar" -eq 0 ] && [ "$cp_sha" -eq 0 ] && [ "$size" = "$EXPECT_SIZE" ] && [ "$sha" = "$EXPECT_SHA" ] \
  && [ "$check" = "OK" ]; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
