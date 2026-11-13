#!/usr/bin/env bash
# V14 step H08f-0 (evidence_v2/V14/STEPS.md): install the operator's diagnosis helper into the private root as
# /root/v14/R/private/msca_dn_original/esr_work/v14_diag.py (mode 600), so nothing is pasted into a terminal.
# The helper travels inside this script as gzip + base64. Its source is host/v14_diag.py, byte-equal to the file
# the operator named, sha256 ad713d511984b14b652551f32a09786185ed4c5efcb040fc0013e8539ce72096.
# The script decodes it, refuses unless the sha256 matches, and checks that it parses. It does not run it.
# Prints key=value lines only. No model call, no AWS call. Refuses if a different v14_diag.py is already there.
# Sent alone by deploy/aws/scripts/host-run.ps1 (Run Command, as root). The last line is RESULT=expected or
# RESULT=unexpected. V14_W and V14_PY override the host for the workstation rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${V14_W:-/root/v14}"
PY="${V14_PY:-/opt/msca-dn-anonymisation/python/bin/python3}"
DIR="$W/R/private/msca_dn_original/esr_work"
DEST="$DIR/v14_diag.py"
EXPECT=ad713d511984b14b652551f32a09786185ed4c5efcb040fc0013e8539ce72096
echo "CHECK=v14-h08f-install"
echo "expected_sha256=$EXPECT"
if [ ! -d "$DIR" ] || [ ! -x "$PY" ]; then
  echo "esr_work=absent"
  echo "RESULT=unexpected"
  exit 0
fi
if [ -e "$DEST" ]; then
  have=$(sha256sum "$DEST" | cut -d' ' -f1)
  echo "existing_sha256=$have"
  if [ "$have" = "$EXPECT" ]; then
    echo "already_installed=yes"
    echo "RESULT=expected"
  else
    echo "refused=a different v14_diag.py is already in esr_work"
    echo "RESULT=unexpected"
  fi
  exit 0
fi
tmp=$(mktemp "$DIR/.v14_diag.XXXXXX")
base64 -d <<'B64' | gunzip -c > "$tmp"
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
B64
got=$(sha256sum "$tmp" | cut -d' ' -f1)
echo "payload_sha256=$got"
if [ "$got" != "$EXPECT" ]; then
  rm -f "$tmp"
  echo "refused=payload sha256 differs"
  echo "RESULT=unexpected"
  exit 0
fi
if ! "$PY" -c 'import ast, sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' "$tmp" 2>/dev/null; then
  rm -f "$tmp"
  echo "refused=payload does not parse"
  echo "RESULT=unexpected"
  exit 0
fi
mv "$tmp" "$DEST"
chmod 600 "$DEST"
echo "installed=private/msca_dn_original/esr_work/v14_diag.py size=$(stat -c %s "$DEST") sha256=$(sha256sum "$DEST" | cut -d' ' -f1) mode=$(stat -c %a "$DEST")"
echo "parses=yes"
echo "RESULT=expected"
exit 0
