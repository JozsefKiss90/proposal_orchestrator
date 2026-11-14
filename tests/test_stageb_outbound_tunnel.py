"""Stage B ticket B01: the host packs ``outbound/`` and serves the archive once, on loopback.

``evidence_v2/SB/host/sb_outbound_serve.sh`` packs every regular file under ``$SB_W/outbound`` into one
reproducible archive, serves it at ``http://127.0.0.1:<PO_PORT>/<PO_TOKEN>/<PO_ARCHIVE>`` until one complete
GET or the end of the window, deletes it and ends. ``sb_smoke_seed.sh`` writes the invented file the live
smoke (B04) sends. These tests run both scripts under Git Bash with ``SB_W`` and ``SB_PY`` pointing at a
temporary folder and this Python, over invented files, and skip where Git Bash is absent.

Stage B ticket B02: ``evidence_v2/SB/workstation/sb_fetch.ps1`` starts B01's script by ``host-run.ps1``,
opens an ``AWS-StartPortForwardingSession`` tunnel, downloads the archive and checks it against the host's
sha256. Its tests run the real script under Windows PowerShell against ``tests/fixtures/fake_aws_tunnel.py``,
a shimmed ``aws`` whose ``send-command`` runs B01's real script under Git Bash and whose ``start-session``
relays loopback ports, and skip where either shell is absent.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import queue
import re
import secrets
import shutil
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import pytest

from tests.test_aws_host_lifecycle_scripts import BASH

REPO = Path(__file__).resolve().parents[1]
HOST = REPO / "docs" / "infrastructure_security" / "evidence_v2" / "SB" / "host"
SERVE = HOST / "sb_outbound_serve.sh"
SEED = HOST / "sb_smoke_seed.sh"
ARCHIVE = "out-20261114-a1b2c3.tar.gz"
KEYS = {"CHECK", "interpreter", "refused", "archive_bytes", "archive_sha256", "members", "listening",
        "served", "bytes_sent", "refused_requests", "window_seconds", "archive_deleted", "interrupted", "error",
        "RESULT"}

needs_bash = pytest.mark.skipif(not BASH, reason="no Git Bash")
posix_only = pytest.mark.skipif(os.name != "posix", reason="needs POSIX signals or FIFOs")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _closed(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return False
    except OSError:
        return True


def _env(work: Path, **over: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PO_", "SB_"))}
    env.update({"SB_W": work.as_posix(), "SB_PY": Path(sys.executable).as_posix()})
    env.update(over)
    return env


def _outbound(work: Path, files: dict[str, bytes]) -> Path:
    out = work / "outbound"
    out.mkdir(parents=True, exist_ok=True)
    for name, blob in files.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    return out


class Serve:
    """One run of the serve script, read line by line while it runs."""

    def __init__(self, work: Path, token: Optional[str] = None, port: Optional[int] = None, **over: str) -> None:
        self.work = work
        self.token = secrets.token_hex(32) if token is None else token
        self.port = _free_port() if port is None else port
        vars_ = {"PO_TOKEN": self.token, "PO_ARCHIVE": ARCHIVE, "PO_PORT": str(self.port)}
        vars_.update(over)
        self.started = time.monotonic()
        self.elapsed = 0.0
        self.proc = subprocess.Popen([BASH, SERVE.as_posix()], env=_env(work, **vars_), stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        self.lines: list[str] = []
        self._q: "queue.Queue[Optional[str]]" = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        assert self.proc.stdout is not None
        for raw in self.proc.stdout:
            self._q.put(raw.decode("ascii", "replace").rstrip("\r\n"))
        self._q.put(None)

    def drain(self) -> None:
        """Collect every line left, up to the end of the output."""
        while True:
            try:
                line = self._q.get(timeout=10)
            except queue.Empty:
                raise AssertionError(f"output did not end; got {self.lines}")
            if line is None:
                self._q.put(None)
                return
            self.lines.append(line)

    def until(self, key: str, timeout: float = 30) -> Optional[str]:
        """Collect lines until one starts with ``key=``; None if the script ends first."""
        end = time.monotonic() + timeout
        while True:
            try:
                line = self._q.get(timeout=max(0.1, end - time.monotonic()))
            except queue.Empty:
                raise AssertionError(f"no {key}= line within {timeout}s; got {self.lines}")
            if line is None:
                self._q.put(None)
                return None
            self.lines.append(line)
            if line.startswith(key + "="):
                return line.split("=", 1)[1]

    def finish(self, timeout: float = 60) -> dict[str, str]:
        self.proc.wait(timeout=timeout)
        self.elapsed = time.monotonic() - self.started
        self.drain()
        return self.values()

    def values(self) -> dict[str, str]:
        return dict(line.split("=", 1) for line in self.lines if "=" in line)

    @property
    def path(self) -> str:
        return f"/{self.token}/{ARCHIVE}"

    def request(self, method: str, path: Optional[str] = None, body: Optional[bytes] = None) -> tuple[int, bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            conn.request(method, path or self.path, body=body)
            resp = conn.getresponse()
            return resp.status, resp.read()
        finally:
            conn.close()

    def kill(self) -> None:
        if self.proc.poll() is None:
            if os.name == "nt":  # killing Git Bash alone would orphan its native Python server
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True, check=False)
            else:
                self.proc.kill()
            self.proc.wait(timeout=10)


@pytest.fixture
def runs():
    started: list[Serve] = []
    yield started
    for run in started:
        run.kill()


def _serve(runs: list[Serve], work: Path, token: Optional[str] = None, port: Optional[int] = None,
           **over: str) -> Serve:
    run = Serve(work, token=token, port=port, **over)
    runs.append(run)
    return run


# ---------------------------------------------------------------------------
# Static checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [SERVE, SEED], ids=lambda p: p.name)
def test_the_scripts_are_ascii_lf_and_end_with_a_result_line(path: Path) -> None:
    data = path.read_bytes()
    data.decode("ascii")
    assert b"\r" not in data
    text = data.decode("ascii")
    assert 'echo "RESULT=expected"' in text and 'echo "RESULT=unexpected"' in text
    assert text.rstrip().splitlines()[-1] == "exit 0"
    assert "0.0.0.0" not in text and "set -x" not in text


@needs_bash
@pytest.mark.parametrize("path", [SERVE, SEED], ids=lambda p: p.name)
def test_the_scripts_parse_in_bash(path: Path) -> None:
    result = subprocess.run([BASH, "-n", path.as_posix()], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr


def test_the_token_is_compared_in_constant_time_and_no_request_is_logged() -> None:
    text = SERVE.read_text(encoding="ascii")
    assert "hmac.compare_digest" in text
    assert "http.server" not in text and "log_message" not in text


# ---------------------------------------------------------------------------
# Serving once
# ---------------------------------------------------------------------------


@needs_bash
def test_the_happy_path_serves_the_archive_once_and_cleans_up(tmp_path, runs) -> None:
    _outbound(tmp_path, {"B1/section_1_2.md": b"invented draft text\n", "notes.txt": b"invented notes\n"})
    run = _serve(runs, tmp_path)
    assert run.until("listening") == f"127.0.0.1:{run.port}"
    status, body = run.request("GET")
    values = run.finish()
    assert status == 200
    assert hashlib.sha256(body).hexdigest() == values["archive_sha256"]
    assert int(values["archive_bytes"]) == len(body)
    assert values["members"] == "2"
    assert values["served"] == "yes" and values["bytes_sent"] == values["archive_bytes"]
    assert values["archive_deleted"] == "yes" and values["RESULT"] == "expected"
    assert run.lines[-1] == "RESULT=expected"
    assert not (tmp_path / "export" / ARCHIVE).exists()
    assert _closed(run.port)


@needs_bash
def test_a_second_get_after_the_served_one_is_refused_at_the_socket(tmp_path, runs) -> None:
    _outbound(tmp_path, {"a.md": b"invented\n"})
    run = _serve(runs, tmp_path)
    run.until("listening")
    assert run.request("GET")[0] == 200
    run.finish()
    with pytest.raises(OSError):
        run.request("GET")


@needs_bash
def test_wrong_requests_are_refused_counted_and_do_not_end_the_server(tmp_path, runs) -> None:
    _outbound(tmp_path, {"a.md": b"invented\n"})
    run = _serve(runs, tmp_path)
    run.until("listening")
    wrong_token = f"/{secrets.token_hex(32)}/{ARCHIVE}"
    wrong_name = f"/{run.token}/out-20261114-ffffff.tar.gz"
    seen = [run.request("GET", wrong_token), run.request("GET", wrong_name), run.request("GET", "/"),
            run.request("HEAD"), run.request("POST", body=b"x"), run.request("PUT", body=b"x")]
    assert [s for s, _ in seen] == [404, 404, 404, 405, 405, 405]
    assert all(b == b"" for _, b in seen)
    with socket.create_connection(("127.0.0.1", run.port), timeout=10) as s:
        s.sendall(b"garbage\r\n\r\n")
        assert s.recv(1024).startswith(b"HTTP/1.1 404")
    assert run.proc.poll() is None
    status, body = run.request("GET")
    values = run.finish()
    assert status == 200 and hashlib.sha256(body).hexdigest() == values["archive_sha256"]
    assert values["refused_requests"] == "7"
    assert values["RESULT"] == "expected"


@needs_bash
def test_a_client_that_drops_mid_body_does_not_end_the_server(tmp_path, runs) -> None:
    _outbound(tmp_path, {"big.bin": os.urandom(12_000_000)})
    run = _serve(runs, tmp_path, PO_MAX_BYTES="30000000")
    run.until("listening")
    with socket.create_connection(("127.0.0.1", run.port), timeout=10) as s:
        s.sendall(f"GET {run.path} HTTP/1.1\r\nHost: x\r\n\r\n".encode("ascii"))
        got = s.recv(65536)
        assert got.startswith(b"HTTP/1.1 200")
        # Drop with a reset. A graceful close after a partial read cannot be told from a complete one when
        # the kernel has buffered the whole archive; the workstation's sha256 check covers that case (B02).
        s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    time.sleep(1)
    assert run.proc.poll() is None
    assert not any(line == "served=yes" for line in run.lines)
    try:
        status, body = run.request("GET")
    except ConnectionResetError:
        # served=yes means sent, not received: Windows can cut this client off after every byte was sent
        # (3 of 30 runs). The workstation's sha256 check is what proves delivery (B02, B03).
        status, body = None, b""
    values = run.finish()
    assert values["served"] == "yes" and values["bytes_sent"] == values["archive_bytes"]
    assert values["RESULT"] == "expected"
    if status is not None:
        assert status == 200 and hashlib.sha256(body).hexdigest() == values["archive_sha256"]


@needs_bash
def test_a_window_without_a_fetch_ends_unexpected_and_deletes_the_archive(tmp_path, runs) -> None:
    _outbound(tmp_path, {"a.md": b"invented\n"})
    run = _serve(runs, tmp_path, PO_WINDOW_SECONDS="30")
    run.until("listening")
    values = run.finish(timeout=60)
    assert run.elapsed <= 35
    assert values["served"] == "no" and values["window_seconds"] == "30"
    assert values["archive_deleted"] == "yes" and values["RESULT"] == "unexpected"
    assert not (tmp_path / "export" / ARCHIVE).exists()


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------


def _refused(runs: list[Serve], work: Path, token: Optional[str] = None, port: Optional[int] = None,
             **over: str) -> dict[str, str]:
    run = _serve(runs, work, token=token, port=port, **over)
    values = run.finish(timeout=30)
    assert "listening" not in values, run.lines
    assert values.get("refused"), run.lines
    assert run.lines[-1] == "RESULT=unexpected"
    assert not (work / "export" / ARCHIVE).exists()
    return values


@needs_bash
@pytest.mark.parametrize("token", ["", "abc123", "g" * 64, "a" * 63], ids=["missing", "short", "not-hex", "63"])
def test_a_bad_token_is_refused(tmp_path, runs, token) -> None:
    _outbound(tmp_path, {"a.md": b"invented\n"})
    port = _free_port()
    _refused(runs, tmp_path, token=token, port=port)
    assert _closed(port)


@needs_bash
@pytest.mark.parametrize("name", ["", "draft.tar.gz", "out-2026114-a1b2c3.tar.gz", "../out-20261114-a1b2c3.tar.gz",
                                  "out-20261114-A1B2C3.tar.gz"])
def test_a_bad_archive_name_is_refused(tmp_path, runs, name) -> None:
    _outbound(tmp_path, {"a.md": b"invented\n"})
    _refused(runs, tmp_path, PO_ARCHIVE=name)


@needs_bash
@pytest.mark.parametrize("over", [{"PO_PORT": "80"}, {"PO_PORT": "70000"}, {"PO_WINDOW_SECONDS": "10"},
                                  {"PO_WINDOW_SECONDS": "901"}, {"PO_MAX_BYTES": "x"}], ids=str)
def test_out_of_range_settings_are_refused(tmp_path, runs, over) -> None:
    _outbound(tmp_path, {"a.md": b"invented\n"})
    _refused(runs, tmp_path, **over)


@needs_bash
@pytest.mark.parametrize("files", [{"notes..txt": b"x"}, {".env": b"x"}, {"sub/.hidden/a.md": b"x"},
                                   {"bad name.md": b"x"}, {"café.md": b"x"}],
                         ids=["dotdot", "hidden-file", "hidden-dir", "space", "non-ascii"])
def test_a_name_that_may_not_leave_is_refused(tmp_path, runs, files) -> None:
    _outbound(tmp_path, {"ok.md": b"invented\n", **files})
    _refused(runs, tmp_path)


@needs_bash
def test_a_symlink_is_refused(tmp_path, runs) -> None:
    out = _outbound(tmp_path, {"ok.md": b"invented\n"})
    target = tmp_path / "elsewhere.txt"
    target.write_bytes(b"not for export\n")
    try:
        (out / "link.md").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks cannot be made here")
    _refused(runs, tmp_path)


@needs_bash
@posix_only
def test_a_file_that_is_not_regular_is_refused(tmp_path, runs) -> None:
    out = _outbound(tmp_path, {"ok.md": b"invented\n"})
    os.mkfifo(out / "pipe")
    _refused(runs, tmp_path)


@needs_bash
@posix_only
def test_sigterm_deletes_the_archive_and_ends_unexpected(tmp_path, runs) -> None:
    _outbound(tmp_path, {"a.md": b"invented\n"})
    run = _serve(runs, tmp_path)
    run.until("listening")
    assert (tmp_path / "export" / ARCHIVE).exists()
    run.proc.send_signal(signal.SIGTERM)
    values = run.finish(timeout=30)
    assert values["interrupted"] == "yes" and values["served"] == "no"
    assert values["archive_deleted"] == "yes" and run.lines[-1] == "RESULT=unexpected"
    assert not (tmp_path / "export" / ARCHIVE).exists()
    assert _closed(run.port)


@needs_bash
def test_an_empty_or_absent_folder_is_refused(tmp_path, runs) -> None:
    _refused(runs, tmp_path)
    (tmp_path / "outbound" / "empty_dir").mkdir(parents=True)
    _refused(runs, tmp_path)


@needs_bash
def test_a_total_above_the_cap_is_refused(tmp_path, runs) -> None:
    _outbound(tmp_path, {"a.md": b"x" * 600, "b.md": b"y" * 600})
    _refused(runs, tmp_path, PO_MAX_BYTES="1000")


@needs_bash
def test_a_busy_port_is_refused_before_packing(tmp_path, runs) -> None:
    _outbound(tmp_path, {"a.md": b"invented\n"})
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        values = _refused(runs, tmp_path, port=busy.getsockname()[1])
    assert "archive_sha256" not in values


# ---------------------------------------------------------------------------
# Reproducibility, loopback, metadata
# ---------------------------------------------------------------------------


@needs_bash
def test_two_runs_over_the_same_folder_give_the_same_archive(tmp_path, runs) -> None:
    out = _outbound(tmp_path, {"z.md": b"invented z\n", "a/b.md": b"invented b\n", "m.txt": b"invented m\n"})
    hashes = []
    for i in range(2):
        if i:
            os.utime(out / "z.md", (1_000_000, 1_000_000))
        run = _serve(runs, tmp_path)
        run.until("listening")
        status, body = run.request("GET")
        values = run.finish()
        assert status == 200 and values["RESULT"] == "expected"
        hashes.append(values["archive_sha256"])
        assert hashlib.sha256(body).hexdigest() == values["archive_sha256"]
    assert hashes[0] == hashes[1]


def _non_loopback_address() -> Optional[str]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # TEST-NET-1; a UDP connect sends nothing
            ip = s.getsockname()[0]
    except OSError:
        return None
    return None if ip.startswith("127.") or ip == "0.0.0.0" else ip


@needs_bash
def test_a_connection_to_the_non_loopback_address_is_refused(tmp_path, runs) -> None:
    ip = _non_loopback_address()
    if not ip:
        pytest.skip("no non-loopback address")
    _outbound(tmp_path, {"a.md": b"invented\n"})
    run = _serve(runs, tmp_path)
    run.until("listening")
    assert _closed(run.port, ip)
    assert run.request("GET")[0] == 200
    run.finish()


@needs_bash
def test_stdout_holds_neither_member_names_nor_the_token(tmp_path, runs) -> None:
    names = {"secretmembername-7f3a.md": b"invented body alpha\n", "dir-q9z/othermember-k2.txt": b"invented beta\n"}
    _outbound(tmp_path, names)
    token = "0123456789abcdef" * 4
    run = _serve(runs, tmp_path, token=token)
    run.until("listening")
    assert run.request("GET")[0] == 200
    run.finish()
    text = "\n".join(run.lines)
    stderr = run.proc.stderr.read().decode("ascii", "replace") if run.proc.stderr else ""
    for secret in [token, "secretmembername", "othermember", "dir-q9z", "invented body"]:
        assert secret not in text and secret not in stderr
    for line in run.lines:
        assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=[ -~]*", line), line
        assert line.split("=", 1)[0] in KEYS, line


# ---------------------------------------------------------------------------
# The smoke seed
# ---------------------------------------------------------------------------


def _seed(work: Path, **over: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([BASH, SEED.as_posix()], env=_env(work, **over), capture_output=True, text=True,
                          timeout=60, check=False)


@needs_bash
def test_the_seed_writes_exactly_po_bytes_of_invented_text(tmp_path) -> None:
    result = _seed(tmp_path, PO_BYTES="123457")
    lines = result.stdout.splitlines()
    assert lines[-1] == "RESULT=expected", result.stdout + result.stderr
    files = [p for p in (tmp_path / "outbound").rglob("*") if p.is_file()]
    assert len(files) == 1
    blob = files[0].read_bytes()
    assert len(blob) == 123457
    blob.decode("ascii")
    values = dict(x.split("=", 1) for x in lines)
    assert values["seed_bytes"] == "123457"
    assert values["seed_sha256"] == hashlib.sha256(blob).hexdigest()


@needs_bash
def test_the_seed_refuses_a_non_empty_folder_and_a_bad_size(tmp_path) -> None:
    _outbound(tmp_path, {"draft.md": b"already here\n"})
    result = _seed(tmp_path, PO_BYTES="100")
    assert result.stdout.splitlines()[-1] == "RESULT=unexpected"
    assert (tmp_path / "outbound" / "draft.md").read_bytes() == b"already here\n"
    assert len(list((tmp_path / "outbound").iterdir())) == 1
    for bad in ("", "0", "abc", "999999999"):
        empty = tmp_path / f"w{len(bad)}{bad}"
        assert _seed(empty, PO_BYTES=bad).stdout.splitlines()[-1] == "RESULT=unexpected"
        assert not (empty / "outbound").exists() or not any((empty / "outbound").iterdir())


# ---------------------------------------------------------------------------
# B02: the workstation fetches through the tunnel
# ---------------------------------------------------------------------------

FETCH = REPO / "docs" / "infrastructure_security" / "evidence_v2" / "SB" / "workstation" / "sb_fetch.ps1"
FAKE_TUNNEL = REPO / "tests" / "fixtures" / "fake_aws_tunnel.py"
INSTANCE = "i-0123456789abcdef0"
RECORD_FIELDS = {"archive", "bytes", "local_sha256", "host_sha256", "sha256_match", "instance_id", "command_id",
                 "session_id", "document_name", "host_port", "local_port", "start_utc", "end_utc", "host_lines"}

WINDOWS_POWERSHELL = shutil.which("powershell")  # 5.1, the version the script is written for; never pwsh
try:
    import psutil
except ImportError:  # the cleanup checks need it; the tunnel tests skip without it
    psutil = None

needs_tunnel = pytest.mark.skipif(not (WINDOWS_POWERSHELL and BASH and psutil and os.name == "nt"),
                                  reason="needs Windows PowerShell 5.1, Git Bash and psutil")


def _live(tmp: Path) -> list[str]:
    """Command lines of running processes that name this test's folder."""
    found = []
    for proc in psutil.process_iter(["pid", "name"]):
        if not str(proc.info["name"]).lower().startswith(("python", "py.", "bash", "sh.", "powershell", "cmd", "aws",
                                                           "session-manager")):
            continue
        try:
            line = " ".join(proc.cmdline() or [])
        except (psutil.Error, TypeError):
            continue
        if str(tmp) in line or tmp.as_posix() in line:
            found.append(f"{proc.info['pid']}: {line}")
    return found


def _kill_live(tmp: Path) -> None:
    for entry in _live(tmp):
        try:
            psutil.Process(int(entry.split(":", 1)[0])).kill()
        except psutil.Error:
            pass


class Fetched:
    def __init__(self, tmp: Path, result: subprocess.CompletedProcess[str], out: Path, dest: Path) -> None:
        self.tmp, self.out, self.dest = tmp, out, dest
        self.rc = result.returncode
        self.stdout, self.stderr = result.stdout, result.stderr
        self.elapsed = 0.0
        log = tmp / "state" / "calls"
        self.calls = [json.loads(x.read_text(encoding="utf-8")) for x in sorted(log.glob("*.json"))]

    def ops(self, op: str) -> list[dict]:
        return [c for c in self.calls if " ".join(c["argv"][:2]) == op]

    def record(self) -> dict:
        return json.loads(self.out.read_text(encoding="utf-8-sig"))

    def token(self) -> str:
        sent = (self.tmp / "state" / "host.sh").read_text(encoding="ascii")
        found = re.search(r"^export PO_TOKEN='([0-9a-f]{64})'$", sent, re.M)
        assert found, "the host received no token"
        return found.group(1)

    def host_values(self) -> dict[str, str]:
        text = (self.tmp / "state" / "host.out").read_text(encoding="ascii")
        return dict(x.split("=", 1) for x in text.splitlines() if "=" in x)


@pytest.fixture
def tunnel_tmp(tmp_path):
    yield tmp_path
    if psutil:
        _kill_live(tmp_path)


def _fetch(tmp: Path, files: Optional[dict[str, bytes]] = None, relay: str = "", alter: str = "", delay: str = "",
           shims: tuple[str, ...] = ("aws", "plugin"), instance: Optional[str] = INSTANCE,
           dest: Optional[Path] = None, out: Optional[Path] = None, serve: Optional[Path] = None) -> Fetched:
    work = tmp / "host"
    (work / "outbound").mkdir(parents=True, exist_ok=True)
    if files:
        _outbound(work, files)
    for name in ("state", "temp", "shims"):
        (tmp / name).mkdir(exist_ok=True)
    if "aws" in shims:
        (tmp / "shims" / "aws.cmd").write_text(f'@"{sys.executable}" "{FAKE_TUNNEL}" %*\r\n', encoding="ascii")
    if "plugin" in shims:
        (tmp / "shims" / "session-manager-plugin.cmd").write_text("@exit /b 0\r\n", encoding="ascii")
    outputs = tmp / "outputs.json"
    rows = [{"OutputKey": "VpcId", "OutputValue": "vpc-0abc"}]
    if instance:
        rows.append({"OutputKey": "InstanceId", "OutputValue": instance})
    outputs.write_text(json.dumps(rows), encoding="utf-8")
    if dest is None:
        dest = tmp / "private"
        dest.mkdir(exist_ok=True)
    out = out or tmp / "evidence.json"
    root = os.environ.get("SystemRoot", r"C:\WINDOWS")
    path = os.pathsep.join([str(tmp / "shims"), os.path.join(root, "System32"), root,
                            os.path.join(root, "System32", "WindowsPowerShell", "v1.0")])
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PO_", "SB_", "FAKE_", "AWS_"))}
    env.update({"PATH": path, "TEMP": str(tmp / "temp"), "TMP": str(tmp / "temp"), "PO_POLL_SECONDS": "1",
                "FAKE_TUNNEL_DIR": str(tmp / "state"), "FAKE_TUNNEL_BASH": str(BASH),
                "FAKE_TUNNEL_SB_W": work.as_posix(), "FAKE_TUNNEL_RELAY": relay, "FAKE_TUNNEL_ALTER": alter,
                "FAKE_TUNNEL_DELAY": delay})
    argv = [str(WINDOWS_POWERSHELL), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(FETCH),
            "-AwsProfile", "po-r1", "-Outputs", str(outputs), "-Dest", str(dest), "-Out", str(out),
            "-HostPort", str(_free_port()), "-WindowSeconds", "30"]
    if serve is not None:
        argv += ["-ServeScript", str(serve)]
    started = time.monotonic()
    result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=300, check=False)
    fetched = Fetched(tmp, result, out, dest)
    fetched.elapsed = time.monotonic() - started
    return fetched


def _assert_cleaned_up(f: Fetched) -> None:
    left = [p.name for p in (f.tmp / "temp").iterdir() if p.name.startswith("po-")]  # not other programs' files
    assert not left, f"the temp folder still holds {left}"
    assert not list(f.dest.glob("*.part"))
    assert len(f.ops("ssm terminate-session")) == 1
    assert (f.tmp / "state" / "host.rc").exists(), "the host script is still running"
    assert not _live(f.tmp), _live(f.tmp)


def test_the_fetch_script_is_ascii() -> None:
    FETCH.read_bytes().decode("ascii")


@needs_tunnel
@pytest.mark.parametrize("case, why", [
    ("out_exists", "a run never overwrites"), ("dest_missing", "is not a folder"),
    ("dest_in_git", "inside a git work tree"), ("dest_in_repo", "under this repository"),
    ("no_aws", "AWS CLI"), ("no_plugin", "Session Manager plugin"), ("no_instance", "holds no InstanceId"),
    ("no_serve", "not found")])
def test_each_refusal_exits_2_before_any_aws_call(tunnel_tmp, case, why) -> None:
    kw: dict = {}
    if case == "out_exists":
        kw["out"] = tunnel_tmp / "evidence.json"
        kw["out"].write_text("{}", encoding="utf-8")
    elif case == "dest_missing":
        kw["dest"] = tunnel_tmp / "absent"
    elif case == "dest_in_git":
        (tunnel_tmp / "wt" / ".git").mkdir(parents=True)
        kw["dest"] = tunnel_tmp / "wt" / "private"
        kw["dest"].mkdir()
    elif case == "dest_in_repo":
        kw["dest"] = REPO / "tests" / "fixtures"
    elif case == "no_aws":
        kw["shims"] = ("plugin",)
    elif case == "no_plugin":
        kw["shims"] = ("aws",)
    elif case == "no_instance":
        kw["instance"] = None
    elif case == "no_serve":
        kw["serve"] = tunnel_tmp / "absent.sh"
    f = _fetch(tunnel_tmp, files={"notes.txt": b"invented\n"}, **kw)
    assert f.rc == 2, f.stdout + f.stderr
    assert f.calls == []
    assert "REFUSED" in f.stdout and why in f.stdout, f.stdout
    if case != "out_exists":
        assert not f.out.exists()


@needs_tunnel
def test_the_happy_path_keeps_the_archive_equal_to_the_hosts(tunnel_tmp) -> None:
    f = _fetch(tunnel_tmp, files={"B1/section_1_2.md": b"invented draft text\n", "notes.txt": b"invented notes\n"})
    assert f.rc == 0, f.stdout + f.stderr
    host = f.host_values()
    assert host["RESULT"] == "expected"
    kept = list(f.dest.iterdir())
    assert len(kept) == 1 and re.fullmatch(r"out-\d{8}-[0-9a-f]{6}\.tar\.gz", kept[0].name)
    blob = kept[0].read_bytes()
    assert hashlib.sha256(blob).hexdigest() == host["archive_sha256"]
    assert len(blob) == int(host["archive_bytes"])
    assert len(f.ops("ssm send-command")) == 1
    sessions = f.ops("ssm start-session")
    assert len(sessions) == 1
    argv = sessions[0]["argv"]
    assert argv[argv.index("--document-name") + 1] == "AWS-StartPortForwardingSession"
    assert argv[argv.index("--target") + 1] == INSTANCE
    params = json.loads(next(iter(sessions[0]["files"].values())))
    record = f.record()
    assert params == {"portNumber": [str(record["host_port"])], "localPortNumber": [str(record["local_port"])]}
    terminated = f.ops("ssm terminate-session")[0]["argv"]
    assert terminated[terminated.index("--session-id") + 1] == record["session_id"]
    _assert_cleaned_up(f)


@needs_tunnel
def test_a_host_that_starts_serving_late_still_delivers(tunnel_tmp) -> None:
    # 100 s is past the window plus 60 s: the poll must follow host-run, not a clock started at the session.
    f = _fetch(tunnel_tmp, files={"notes.txt": b"invented notes\n"}, delay="100")
    assert f.rc == 0, f.stdout + f.stderr
    assert f.host_values()["RESULT"] == "expected"
    assert f.elapsed >= 100
    _assert_cleaned_up(f)


@needs_tunnel
def test_the_token_appears_nowhere_but_the_host(tunnel_tmp) -> None:
    f = _fetch(tunnel_tmp, files={"notes.txt": b"invented notes\n"})
    assert f.rc == 0, f.stdout + f.stderr
    token = f.token()
    assert token not in f.out.read_text(encoding="utf-8-sig")
    assert token not in f.stdout and token not in f.stderr


@needs_tunnel
def test_the_record_carries_the_decided_fields_and_nothing_secret(tunnel_tmp) -> None:
    f = _fetch(tunnel_tmp, files={"notes.txt": b"invented notes\n"})
    assert f.rc == 0, f.stdout + f.stderr
    record = f.record()
    assert RECORD_FIELDS <= set(record)
    assert record["sha256_match"] is True and record["session_terminated"] is True
    assert record["command_id"] and record["session_id"] and record["local_port"]
    assert record["local_sha256"] == record["host_sha256"] == f.host_values()["archive_sha256"]
    assert record["instance_id"] == INSTANCE
    assert record["document_name"] == "AWS-StartPortForwardingSession"
    assert record["host_lines"]["RESULT"] == "expected"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", record["start_utc"])
    assert "token" not in json.dumps(record).lower()


@needs_tunnel
def test_a_host_refusal_keeps_nothing_and_ends_the_session(tunnel_tmp) -> None:
    f = _fetch(tunnel_tmp, files=None)
    assert f.rc == 1, f.stdout + f.stderr
    assert f.host_values()["RESULT"] == "unexpected"
    assert list(f.dest.iterdir()) == []
    _assert_cleaned_up(f)


@needs_tunnel
def test_a_different_host_sha256_deletes_the_local_file(tunnel_tmp) -> None:
    f = _fetch(tunnel_tmp, files={"notes.txt": b"invented notes\n"}, alter="sha")
    assert f.rc == 1, f.stdout + f.stderr
    assert list(f.dest.iterdir()) == []
    assert f.record()["sha256_match"] is False
    _assert_cleaned_up(f)


@needs_tunnel
def test_a_tunnel_that_carries_nothing_ends_after_the_window(tunnel_tmp) -> None:
    f = _fetch(tunnel_tmp, files={"notes.txt": b"invented notes\n"}, relay="none")
    assert f.rc == 1, f.stdout + f.stderr
    assert list(f.dest.iterdir()) == []
    assert f.host_values()["served"] == "no"
    assert f.elapsed >= 30, "the fetch ended before the host's window"
    _assert_cleaned_up(f)
