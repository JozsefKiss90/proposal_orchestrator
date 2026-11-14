"""A fake AWS CLI for the Stage B tunnel tests (ticket B02).

Every call writes ``{"argv": [...], "files": {...}}`` to its own file in ``$FAKE_TUNNEL_DIR/calls/``, named
by time and process id, since several calls run at once; a ``file://`` argument is read at call time, as the
real CLI reads it. The fake keeps its state in ``FAKE_TUNNEL_DIR``:

- ``ssm send-command`` writes the sent lines to ``host.sh`` and runs them in a detached runner under
  ``FAKE_TUNNEL_BASH`` with ``SB_W=$FAKE_TUNNEL_SB_W`` and ``SB_PY`` this Python, so B01's real script
  serves. The runner writes ``host.out``, then ``host.rc`` when the script ends. ``FAKE_TUNNEL_DELAY=<s>``
  holds the script back that long, as a host slow to start would.
- ``ssm get-command-invocation`` answers ``InProgress`` until ``host.rc`` exists, then that run's status
  and stdout. ``FAKE_TUNNEL_ALTER=sha`` replaces the ``archive_sha256`` value with zeros.
- ``ssm start-session`` prints a ``SessionId`` as the plugin does and relays each connection on
  ``127.0.0.1:<localPortNumber>`` to ``127.0.0.1:<portNumber>`` until killed. ``FAKE_TUNNEL_RELAY=none``
  accepts and closes each connection without relaying.
- ``ssm terminate-session`` answers as the real CLI does.

``session-manager-plugin`` is a separate shim that only needs to exist on PATH.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

COMMAND_ID = "0b1c2d3e-4f50-6172-8394-a5b6c7d8e9f0"
SESSION_ID = "po-r1-0a1b2c3d4e5f60718"


def state() -> Path:
    return Path(os.environ["FAKE_TUNNEL_DIR"])


def arg(args: list[str], name: str) -> str:
    return args[args.index(name) + 1]


def parameters(args: list[str]) -> dict:
    value = arg(args, "--parameters")
    if value.startswith("file://"):
        value = Path(value[7:]).read_text(encoding="utf-8")
    return json.loads(value)


def send_command(args: list[str]) -> int:
    lines = parameters(args)["commands"]
    host = state() / "host.sh"
    host.write_bytes(("\n".join(lines) + "\n").encode("ascii"))
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    subprocess.Popen([sys.executable, __file__, "--run-host"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=flags, close_fds=True)
    print(COMMAND_ID)
    return 0


def run_host() -> int:
    time.sleep(float(os.environ.get("FAKE_TUNNEL_DELAY") or 0))
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PO_", "SB_"))}
    env.update({"SB_W": os.environ["FAKE_TUNNEL_SB_W"], "SB_PY": Path(sys.executable).as_posix()})
    with open(state() / "host.out", "wb") as out:
        proc = subprocess.Popen([os.environ["FAKE_TUNNEL_BASH"], (state() / "host.sh").as_posix()], env=env,
                                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.DEVNULL)
        rc = proc.wait()
    (state() / "host.rc").write_text(str(rc), encoding="ascii")
    return 0


def invocation(args: list[str]) -> int:
    done = (state() / "host.rc").exists()
    if "--query" in args:
        print("Success" if done else "InProgress")
        return 0
    stdout = (state() / "host.out").read_bytes().decode("ascii", "replace") if done else ""
    if os.environ.get("FAKE_TUNNEL_ALTER") == "sha":
        stdout = re.sub(r"archive_sha256=[0-9a-f]+", "archive_sha256=" + "0" * 64, stdout)
    status = "Success" if done else "InProgress"
    print(json.dumps({"Status": status, "StatusDetails": status, "ResponseCode": 0 if done else -1,
                      "ExecutionStartDateTime": "2026-11-14T10:00:00Z", "ExecutionEndDateTime": "2026-11-14T10:01:00Z",
                      "StandardOutputContent": stdout, "StandardErrorContent": ""}))
    return 0


def pipe(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            chunk = src.recv(65536)
            if not chunk:
                break
            dst.sendall(chunk)
    except OSError:
        pass
    finally:
        for s in (dst, src):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def relay(client: socket.socket, host_port: int) -> None:
    if os.environ.get("FAKE_TUNNEL_RELAY") == "none":
        client.close()
        return
    try:
        upstream = socket.create_connection(("127.0.0.1", host_port), timeout=5)
    except OSError:
        client.close()
        return
    upstream.settimeout(None)
    back = threading.Thread(target=pipe, args=(upstream, client), daemon=True)
    back.start()
    pipe(client, upstream)
    back.join()
    client.close()
    upstream.close()


def start_session(args: list[str]) -> int:
    params = parameters(args)
    host_port, local_port = int(params["portNumber"][0]), int(params["localPortNumber"][0])
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", local_port))
    srv.listen(8)
    print("", flush=True)
    print(f"Starting session with SessionId: {SESSION_ID}", flush=True)
    print(f"Port {local_port} opened for sessionId {SESSION_ID}.", flush=True)
    print("Waiting for connections...", flush=True)
    while True:
        client, _ = srv.accept()
        threading.Thread(target=relay, args=(client, host_port), daemon=True).start()


def main(argv: list[str]) -> int:
    if argv == ["--run-host"]:
        return run_host()
    args = list(argv)
    files = {}
    for a in args:
        if a.startswith("file://") and os.path.isfile(a[7:]):
            files[a] = Path(a[7:]).read_text(encoding="utf-8", errors="replace")
    calls = state() / "calls"
    calls.mkdir(exist_ok=True)
    (calls / f"{time.time_ns():020d}-{os.getpid()}.json").write_text(json.dumps({"argv": args, "files": files}),
                                                                      encoding="utf-8")
    op = " ".join(args[:2])
    if op == "ssm send-command":
        return send_command(args)
    if op == "ssm get-command-invocation":
        return invocation(args)
    if op == "ssm start-session":
        return start_session(args)
    if op == "ssm terminate-session":
        print(json.dumps({"SessionId": arg(args, "--session-id")}))
        return 0
    sys.stderr.write(f"fake aws: no answer for {op}\n")
    return 255


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
