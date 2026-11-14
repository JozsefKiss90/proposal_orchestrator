#!/usr/bin/env bash
# Stage B ticket B01: write one invented text file into /root/sb/outbound for the live smoke of the
# outbound tunnel (B04). The file holds a repeated invented line and nothing private. Sent alone by
# deploy/aws/scripts/host-run.ps1 with a vars file (Run Command, as root):
#   PO_BYTES   the file's exact size in bytes, 1-20000000
# Refuses an outbound folder that holds anything. Prints key=value lines only; the last line is
# RESULT=expected or RESULT=unexpected. SB_W overrides /root/sb for the workstation rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${SB_W:-/root/sb}"
OUT="$W/outbound"
SIZE="${PO_BYTES:-}"
echo "CHECK=sb-smoke-seed"
fail() { echo "refused=$1"; echo "RESULT=unexpected"; exit 0; }
[[ "$SIZE" =~ ^[1-9][0-9]{0,7}$ ]] && [ "$SIZE" -le 20000000 ] || fail "PO_BYTES must be 1-20000000"
if [ -e "$OUT" ]; then
  [ -d "$OUT" ] && [ -r "$OUT" ] || fail "the outbound folder is unusable"
  [ -z "$(ls -A "$OUT")" ] || fail "the outbound folder is not empty"
fi
mkdir -p "$OUT" && chmod 700 "$OUT" || fail "the outbound folder is unusable"
FILE="$OUT/smoke.txt"
yes "Stage B outbound smoke test. Invented text, nothing private." | head -c "$SIZE" > "$FILE"
got=$(stat -c %s "$FILE" 2>/dev/null || echo 0)
echo "seed_bytes=$got"
echo "seed_sha256=$(sha256sum "$FILE" | cut -d' ' -f1)"
if [ "$got" = "$SIZE" ]; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
