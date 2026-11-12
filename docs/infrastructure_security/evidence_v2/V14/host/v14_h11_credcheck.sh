#!/usr/bin/env bash
# V14 step H11a (evidence_v2/V14/STEPS.md): before the snapshot, look for credential material on the
# root volume (V14-OP7). Scans the places a run could write to: /root, /home, /tmp, /var/tmp, /var/log,
# /var/lib/amazon and /etc. The installed bundle under /opt is not scanned: H04c verified it byte for
# byte against the O5 manifest, and its test fixtures hold example key shapes by design.
# Five value-shaped patterns: an access key id, a temporary access key id, a secret key assignment, a
# secret string with a value, a session token with a value. The patterns are assembled at run time,
# so this file holds none of their literals (evidence_v2 rule).
# Prints counts only: per area, files scanned, files with a hit, hits per pattern; then, for each file
# with a hit, its path and its counts, never a matched value. The last line is RESULT=expected (no
# hit anywhere) or RESULT=unexpected. Sent alone by host-run.ps1 (Run Command, as root).
# V14_SCAN_ROOTS overrides the areas for the workstation rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
PY="${V14_PY:-/opt/msca-dn-anonymisation/python/bin/python3}"
AREAS="${V14_SCAN_ROOTS:-/root /home /tmp /var/tmp /var/log /var/lib/amazon /etc}"
echo "CHECK=v14-h11-credcheck"
[ -x "$PY" ] || { echo "python=absent"; echo "RESULT=unexpected"; exit 0; }
# shellcheck disable=SC2086
"$PY" - $AREAS <<'PYEOF'
import os, re, sys
A, K = "AK", "IA"
pats = {
    "access_key_id": re.compile((A + K + r"[0-9A-Z]{16}").encode()),
    "temporary_key_id": re.compile(("AS" + K + r"[0-9A-Z]{16}").encode()),
    "secret_key_assignment": re.compile(("aws_" + "secret" + r"_access_key\s*[=:]\s*\S{20,}").encode(), re.I),
    "secret_string_value": re.compile(('"Secret' + 'String"' + r'\s*:\s*"[^"]{8,}').encode()),
    "session_token_value": re.compile(('Session' + 'Token' + r'"?\s*[=:]\s*"?[A-Za-z0-9/+=]{40,}').encode()),
}
LIMIT = 64 * 1024 * 1024
dirty = 0
for area in sys.argv[1:]:
    scanned = hit_files = skipped = 0
    totals = dict.fromkeys(pats, 0)
    if not os.path.isdir(area):
        print(f"area={area} present=no")
        continue
    for base, dirs, files in os.walk(area, followlinks=False):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(base, d))]
        for name in files:
            path = os.path.join(base, name)
            try:
                if os.path.islink(path) or not os.path.isfile(path) or os.path.getsize(path) > LIMIT:
                    skipped += 1
                    continue
                data = open(path, "rb").read()
            except OSError:
                skipped += 1
                continue
            scanned += 1
            counts = {k: len(p.findall(data)) for k, p in pats.items()}
            if any(counts.values()):
                hit_files += 1
                for k, v in counts.items():
                    totals[k] += v
                print("hit_file=" + path + " " + " ".join(f"{k}={v}" for k, v in counts.items() if v))
    dirty += hit_files
    print(f"area={area} files_scanned={scanned} files_skipped={skipped} files_with_hit={hit_files} "
          + " ".join(f"{k}={v}" for k, v in totals.items()))
print("RESULT=" + ("expected" if dirty == 0 else "unexpected"))
PYEOF
exit 0
