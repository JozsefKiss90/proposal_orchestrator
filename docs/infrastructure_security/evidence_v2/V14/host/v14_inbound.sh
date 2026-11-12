#!/usr/bin/env bash
# V14 steps H04d, H08a and H08e-2 (evidence_v2/V14/STEPS.md): fetch one inbound archive from the deploy
# bucket's bundles/ prefix, check its sha256, and place its members under the private root /root/v14/R.
# V14-OP1 (neutral name, sha256 after the fetch), V14-A1 (what the input holds), V14-OP9 (the register).
# Sent by deploy/aws/scripts/host-run.ps1 with a vars file (Run Command, as root):
#   PO_KIND             input | esr | register
#   PO_ARCHIVE          input-<YYYYMMDD>-<6 hex>.tar.gz, the object name under bundles/
#   PO_ARCHIVE_SHA256   the archive's sha256, as the workstation packer printed it
#   PO_MEMBER_SHA256    esr and register only: the one member's sha256
# Prints key=value lines only: counts, sizes and hashes, never a member's content or name. The last
# line is RESULT=expected or RESULT=unexpected. Deleting the bucket object is the workstation's step.
# V14_W, V14_APP and V14_PY override the host paths for the workstation rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${V14_W:-/root/v14}"
R="$W/R"
APP="${V14_APP:-/opt/msca-dn-anonymisation/app}"
PY="${V14_PY:-/opt/msca-dn-anonymisation/python/bin/python3}"
SRC=s3://proposal-orchestrator-deploy-797661577394/bundles
ESR_PATH=docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-original-esr.json
ESR_SHA=5c9b9c8e9f89f501e30256aaa90b55921ce2c3673b2218fa2c0bcd6b7d54b0a9
KIND="${PO_KIND:-}"
ARCH="${PO_ARCHIVE:-}"
echo "CHECK=v14-inbound"
echo "kind=$KIND"
fail() { echo "refused=$1"; echo "RESULT=unexpected"; exit 0; }
case "$KIND" in input|esr|register) ;; *) fail "PO_KIND must be input, esr or register" ;; esac
case "$ARCH" in input-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f].tar.gz) ;;
  *) fail "PO_ARCHIVE is not a neutral archive name" ;; esac
[ -x "$PY" ] || fail "the bundle's python is absent"
mkdir -p "$W/inbound" && chmod 700 "$W" "$W/inbound" || fail "workdir unusable"
LOCAL="$W/inbound/$ARCH"
[ -e "$LOCAL" ] && fail "the archive was fetched before; remove $LOCAL first"
if [ -z "${V14_LOCAL_ARCHIVE:-}" ]; then
  aws s3 cp "$SRC/$ARCH" "$LOCAL" --region eu-north-1 --only-show-errors >"$W/inbound/$ARCH.cp.log" 2>&1
  cp_rc=$?
else
  cp "$V14_LOCAL_ARCHIVE" "$LOCAL"; cp_rc=$?
fi
echo "cp_exit=$cp_rc"
[ "$cp_rc" -eq 0 ] || echo "cp_error=$(grep -o '([A-Za-z]*)' "$W/inbound/$ARCH.cp.log" 2>/dev/null | head -n 1 | tr -d '()')"
echo "archive_bytes=$(stat -c %s "$LOCAL" 2>/dev/null || echo absent)"
sha=$(sha256sum "$LOCAL" 2>/dev/null | cut -d' ' -f1)
echo "archive_sha256=${sha:-absent}"
if [ "$cp_rc" -ne 0 ] || [ "$sha" != "${PO_ARCHIVE_SHA256:-}" ]; then
  echo "archive_sha256_matches=no"
  echo "RESULT=unexpected"
  exit 0
fi
echo "archive_sha256_matches=yes"
out=$("$PY" - "$KIND" "$LOCAL" "$R" "$APP" "$W" "${PO_MEMBER_SHA256:-}" "$ESR_PATH" "$ESR_SHA" <<'PYEOF'
import hashlib, os, re, shutil, sys, tarfile
kind, archive, root, app, work, member_sha, esr_path, esr_sha = sys.argv[1:9]
ok = True
def say(k, v):
    print(f"{k}={v}")
def sha_of(data):
    return hashlib.sha256(data).hexdigest()
with tarfile.open(archive, "r:gz") as tf:
    members = tf.getmembers()
    files = [m for m in members if m.isfile()]
    bad = [m for m in members if not (m.isfile() or m.isdir())
           or m.name.startswith("/") or ".." in m.name.split("/")]
    say("members", len(files))
    say("members_refused", len(bad))
    if bad:
        print("RESULT_PY=unexpected"); sys.exit(0)
    data = {m.name: tf.extractfile(m).read() for m in files}
def place(rel, blob):
    dest = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(dest), mode=0o700, exist_ok=True)
    with open(dest, "xb") as handle:
        handle.write(blob)
if kind == "input":
    if os.path.exists(root):
        say("root", "exists"); print("RESULT_PY=unexpected"); sys.exit(0)
    manifests = [n for n in data if re.fullmatch(r"[^/]+(/[^/]+)*/docs/tier4_orchestration_state/dev_graph/imports/[^/]+\.json", n)]
    registers = [n for n in data if re.fullmatch(r"private/[^/]+/fidelity_register_[^/]+\.json", n)]
    ws_prefix = manifests[0].split("/docs/")[0] + "/" if len(manifests) == 1 else None
    ws_files = [n for n in data if ws_prefix and n.startswith(ws_prefix)]
    supplement = [n for n in data if n not in ws_files and n not in registers]
    say("workspace_files", len(ws_files)); say("registers", len(registers))
    say("supplement_files", len(supplement)); say("import_manifests", len(manifests))
    esr_like = [n for n in data if "/esr/" in n and n.endswith("-esr.json")]
    say("esr_records", len(esr_like))
    os.makedirs(root, mode=0o700)
    for name, blob in sorted(data.items()):
        place(name, blob)
    equal = differ = 0
    for name, blob in data.items():
        installed = os.path.join(app, *name.split("/"))
        if os.path.isfile(installed):
            if sha_of(open(installed, "rb").read()) == sha_of(blob):
                equal += 1
            else:
                differ += 1
    say("in_app_equal", equal); say("in_app_differ", differ)
    say("root_mode", oct(os.stat(root).st_mode & 0o777)[2:])
    ok = (len(files) == 19 and len(registers) == 1 and len(manifests) == 1 and len(ws_files) == 8
          and len(supplement) == 10 and not esr_like and equal == 8 and differ == 0
          and (os.name != "posix" or os.stat(root).st_mode & 0o777 == 0o700))
elif kind == "esr":
    names = list(data)
    got = sha_of(data[names[0]]) if len(names) == 1 else ""
    say("member_sha256", got or "none")
    target = os.path.join(root, *esr_path.split("/"))
    say("esr_present_before", "yes" if os.path.exists(target) else "no")
    ok = (os.path.isdir(root) and names == [esr_path] and got == esr_sha and got == member_sha
          and not os.path.exists(target))
    if ok:
        place(esr_path, data[esr_path])
else:
    names = list(data)
    single = len(names) == 1 and re.fullmatch(r"private/[^/]+/fidelity_register_[^/]+\.json", names[0])
    got = sha_of(data[names[0]]) if len(names) == 1 else ""
    say("member_sha256", got or "none")
    target = os.path.join(root, *names[0].split("/")) if single else ""
    before = sha_of(open(target, "rb").read()) if single and os.path.isfile(target) else ""
    say("register_sha256_before", before or "absent")
    ok = bool(single) and bool(before) and got == member_sha and got != before
    if ok:
        keep = os.path.join(work, "register_before_swap")
        os.makedirs(keep, mode=0o700, exist_ok=True)
        shutil.copy2(target, os.path.join(keep, before[:12] + ".json"))
        os.replace(target, target + ".old")
        place(names[0], data[names[0]])
        os.remove(target + ".old")
        say("register_sha256_after", sha_of(open(target, "rb").read()))
        say("register_kept_as", "register_before_swap/" + before[:12] + ".json")
print("RESULT_PY=" + ("expected" if ok else "unexpected"))
PYEOF
)
printf '%s\n' "$out" | grep -v '^RESULT_PY='
rm -f "$LOCAL" "$W/inbound/$ARCH.cp.log"
echo "local_archive_removed=$([ -e "$LOCAL" ] && echo no || echo yes)"
if printf '%s\n' "$out" | grep -qx 'RESULT_PY=expected'; then
  echo "RESULT=expected"
else
  echo "RESULT=unexpected"
fi
exit 0
