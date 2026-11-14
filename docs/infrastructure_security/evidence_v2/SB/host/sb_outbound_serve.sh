#!/usr/bin/env bash
# Stage B ticket B01: pack /root/sb/outbound into one archive and serve it once, on loopback only, for the
# workstation to fetch through a Session Manager port-forward tunnel (B02). Decision record
# msca-dn-stage-b-drafting-lane_2026-11-14, gap G2. Sent alone by deploy/aws/scripts/host-run.ps1 with a
# vars file (Run Command, as root):
#   PO_TOKEN            64 lowercase hex characters, made by the workstation for one fetch; never printed
#   PO_ARCHIVE          out-<YYYYMMDD>-<6 hex>.tar.gz, a neutral name as in V14-OP1
#   PO_PORT             default 8765; 1024-65535
#   PO_WINDOW_SECONDS   default 300; 30-900. The window starts when the socket listens and is a hard end:
#                       a transfer still running when it ends does not count as served.
#   PO_MAX_BYTES        default 20000000; the cap on the members' total size
# Steps: refuse anything that may not leave (symlink, non-regular file, hidden name, a name outside
# [A-Za-z0-9._/-], any ".." in a name, a folder holding no file, a total above the cap) and a busy port;
# empty sub-folders are not members. Pack the archive reproducibly for one interpreter (sorted, mtime 0,
# uid/gid 0, mode 600, gzip mtime 0); serve it at http://127.0.0.1:<PO_PORT>/<PO_TOKEN>/<PO_ARCHIVE> until
# one complete GET or the window's end; delete it. Any other path, token or method gets 404 or 405 with no
# body and is counted. No request is logged. "Complete" means every byte was sent; a client that drops
# mid-body fails the send (the send buffer is kept small), which does not count. TCP cannot prove the client
# read every byte: a drop after the last byte reached the kernel still counts as served. So served=yes
# means sent, not received; on Windows a client was seen cut off after it. Behind the tunnel the peer is the
# SSM agent in any case, so only the workstation's sha256 check proves a complete fetch (B02).
# The window must end before the Run Command timeout: a SIGKILL leaves the archive, and the next run refuses.
# Prints key=value lines only, never a member's name or content; a failure prints only the exception's
# class, as error=. The last line is RESULT=expected (every byte sent once, archive deleted) or
# RESULT=unexpected. SB_W and SB_PY override the host paths for the workstation rehearsal only.
set -u
export HOME="${HOME:-/root}"
umask 077
W="${SB_W:-/root/sb}"
if [ -n "${SB_PY:-}" ]; then
  PY="$SB_PY"
elif [ -x /opt/msca-dn-anonymisation/python/bin/python3 ]; then
  PY=/opt/msca-dn-anonymisation/python/bin/python3
else
  PY=/usr/bin/python3
fi
TOKEN="${PO_TOKEN:-}"
ARCH="${PO_ARCHIVE:-}"
PORT="${PO_PORT:-8765}"
WINDOW="${PO_WINDOW_SECONDS:-300}"
MAXB="${PO_MAX_BYTES:-20000000}"
echo "CHECK=sb-outbound-serve"
echo "interpreter=$PY"
fail() { echo "refused=$1"; echo "RESULT=unexpected"; exit 0; }
[[ "$TOKEN" =~ ^[0-9a-f]{64}$ ]] || fail "PO_TOKEN must be 64 lowercase hex characters"
[[ "$ARCH" =~ ^out-[0-9]{8}-[0-9a-f]{6}\.tar\.gz$ ]] || fail "PO_ARCHIVE is not a neutral archive name"
[[ "$PORT" =~ ^[0-9]{1,5}$ ]] && [ "$PORT" -ge 1024 ] && [ "$PORT" -le 65535 ] || fail "PO_PORT must be 1024-65535"
[[ "$WINDOW" =~ ^[0-9]{1,3}$ ]] && [ "$WINDOW" -ge 30 ] && [ "$WINDOW" -le 900 ] || fail "PO_WINDOW_SECONDS must be 30-900"
[[ "$MAXB" =~ ^[1-9][0-9]{0,9}$ ]] || fail "PO_MAX_BYTES must be a positive whole number"
[ -x "$PY" ] || fail "no python interpreter"
[ -d "$W/outbound" ] || fail "the outbound folder is absent"
EXPORT="$W/export"
mkdir -p "$EXPORT" && chmod 700 "$EXPORT" || fail "the export folder is unusable"
LOCAL="$EXPORT/$ARCH"
STATUS="$EXPORT/serve.status"
[ -e "$LOCAL" ] && fail "an archive of this name is already in export; remove it first"
rm -f "$STATUS"
PID=""
finish() {
  if [ -n "$PID" ]; then kill "$PID" 2>/dev/null; wait "$PID" 2>/dev/null; fi
  rm -f "$LOCAL"
  echo "archive_deleted=$([ -e "$LOCAL" ] && echo no || echo yes)"
  if [ "$(cat "$STATUS" 2>/dev/null)" = "served" ] && [ ! -e "$LOCAL" ]; then
    rm -f "$STATUS"
    echo "RESULT=expected"
  else
    rm -f "$STATUS"
    echo "RESULT=unexpected"
  fi
  exit 0
}
on_signal() { trap - TERM INT HUP; echo "interrupted=yes"; finish; }
trap on_signal TERM INT HUP
# Stderr is discarded because a traceback can name a member; the Python prints error=<class> instead.
"$PY" -u - "$W/outbound" "$LOCAL" "$STATUS" "$TOKEN" "$ARCH" "$PORT" "$WINDOW" "$MAXB" 2>/dev/null <<'PYEOF' &
import gzip, hashlib, hmac, os, re, signal, socket, stat, sys, tarfile, time
outbound, archive, status_path, token, name, port, window, max_bytes = sys.argv[1:9]
port, window, max_bytes = int(port), int(window), int(max_bytes)
NAME = re.compile(r"[A-Za-z0-9._/-]+")
REFUSED, DROPPED = ("refused", 0), ("dropped", 0)


class Refusal(Exception):
    pass


def say(k, v):
    print(f"{k}={v}", flush=True)


def stop(signum, frame):
    raise SystemExit(0)


def members_of(folder):
    """Regular files only, plain names, under the cap; sorted (relative name, path, size)."""
    found = []
    for top, dirs, files in os.walk(folder, followlinks=False):
        for entry in sorted(dirs) + sorted(files):
            full = os.path.join(top, entry)
            rel = os.path.relpath(full, folder).replace(os.sep, "/")
            st = os.lstat(full)
            if stat.S_ISLNK(st.st_mode):
                raise Refusal("outbound holds a symlink")
            if entry.startswith("."):
                raise Refusal("outbound holds a hidden name")
            if ".." in entry:
                raise Refusal("outbound holds a name with ..")
            if not NAME.fullmatch(rel):
                raise Refusal("outbound holds a name outside [A-Za-z0-9._/-]")
            if entry in files:
                if not stat.S_ISREG(st.st_mode):
                    raise Refusal("outbound holds a file that is not regular")
                found.append((rel, full, st.st_size))
    if not found:
        raise Refusal("outbound holds no file")
    if sum(size for _, _, size in found) > max_bytes:
        raise Refusal("outbound is larger than PO_MAX_BYTES")
    return sorted(found)


def bind_loopback():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name == "nt":  # the workstation rehearsal only: Windows SO_REUSEADDR would share a busy port
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(("127.0.0.1", port))
    except OSError:
        srv.close()
        raise Refusal("PO_PORT is busy")
    return srv


def pack(members):
    """Reproducible for one interpreter: sorted members, fixed metadata, gzip mtime 0."""
    with open(archive, "xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tf:
                for rel, full, size in members:
                    info = tarfile.TarInfo(rel)
                    info.size, info.mtime, info.mode = size, 0, 0o600
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    with open(full, "rb") as handle:
                        tf.addfile(info, handle)
    with open(archive, "rb") as handle:
        return handle.read()


def reply(conn, code, text):
    conn.sendall(f"HTTP/1.1 {code} {text}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".encode("ascii"))


def drain(conn, seconds):
    # Wait for the client to close, so that closing here cannot cut off bytes still in flight. What the wait
    # ends with proves nothing either way: Windows can report a clean close as a reset.
    conn.settimeout(seconds)
    try:
        while conn.recv(65536):
            pass
    except OSError:
        pass


def handle(conn, deadline, want, blob):
    """("served", body bytes) for a complete GET of the exact path; REFUSED for any other request, which is
    counted; DROPPED for a transfer the client or the window cut short, which is not counted."""
    head = b""
    while b"\r\n\r\n" not in head and len(head) < 8192:
        conn.settimeout(max(0.05, min(5.0, deadline - time.monotonic())))
        chunk = conn.recv(4096)
        if not chunk:
            return REFUSED
        head += chunk
    parts = head.split(b"\r\n", 1)[0].split(b" ")
    if len(parts) != 3 or not parts[2].startswith(b"HTTP/") or not hmac.compare_digest(parts[1], want):
        reply(conn, 404, "Not Found")
        drain(conn, 0.5)
        return REFUSED
    if parts[0] != b"GET":
        reply(conn, 405, "Method Not Allowed")
        drain(conn, 0.5)
        return REFUSED
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
    conn.sendall((f"HTTP/1.1 200 OK\r\nContent-Type: application/gzip\r\nContent-Length: {len(blob)}\r\n"
                  "Connection: close\r\n\r\n").encode("ascii"))
    sent = 0
    while sent < len(blob):
        left = deadline - time.monotonic()
        if left <= 0:
            return DROPPED
        conn.settimeout(left)
        sent += conn.send(blob[sent:sent + 65536])
    conn.shutdown(socket.SHUT_WR)
    drain(conn, max(0.05, min(30.0, deadline - time.monotonic())))
    return ("served", sent)


def serve(srv, blob):
    want = ("/" + token + "/" + name).encode("ascii")
    served, bytes_sent, refused = False, 0, 0
    try:
        srv.listen(8)
        host, bound = srv.getsockname()[:2]
        say("listening", f"{host}:{bound}")
        deadline = time.monotonic() + window
        while not served:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            srv.settimeout(left)
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                break
            try:
                outcome = handle(conn, deadline, want, blob)
            except OSError:
                outcome = DROPPED
            finally:
                conn.close()
            if outcome == REFUSED:
                refused += 1
            elif outcome[0] == "served":
                served, bytes_sent = True, outcome[1]
    finally:
        srv.close()
        say("served", "yes" if served else "no")
        say("bytes_sent", bytes_sent)
        say("refused_requests", refused)
        say("window_seconds", window)
    return served and bytes_sent == len(blob)


def main():
    members = members_of(outbound)
    srv = bind_loopback()  # before packing, so a busy port packs nothing
    try:
        blob = pack(members)
    except BaseException:
        srv.close()
        raise
    say("archive_bytes", len(blob))
    say("archive_sha256", hashlib.sha256(blob).hexdigest())
    say("members", len(members))
    try:
        ok = serve(srv, blob)
    finally:
        os.remove(archive)
    if ok:
        with open(status_path, "w") as handle:
            handle.write("served")


signal.signal(signal.SIGTERM, stop)
try:
    main()
except Refusal as why:
    say("refused", why)
except SystemExit:
    raise
except BaseException as exc:
    say("error", type(exc).__name__)
PYEOF
PID=$!
wait "$PID"
PID=""
finish
exit 0
