"""Stage B ticket B01: the host packs ``outbound/`` and serves the archive once, on loopback.

``evidence_v2/SB/host/sb_outbound_serve.sh`` packs every regular file under ``$SB_W/outbound`` into one
reproducible archive, serves it at ``http://127.0.0.1:<PO_PORT>/<PO_TOKEN>/<PO_ARCHIVE>`` until one complete
GET or the end of the window, deletes it and ends. ``sb_smoke_seed.sh`` writes the invented file the live
smoke (B04) sends. These tests run both scripts under Git Bash with ``SB_W`` and ``SB_PY`` pointing at a
temporary folder and this Python, over invented files, and skip where Git Bash is absent.
"""
from __future__ import annotations

import hashlib
import http.client
import os
import queue
import re
import secrets
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
    status, body = run.request("GET")
    values = run.finish()
    assert status == 200 and hashlib.sha256(body).hexdigest() == values["archive_sha256"]
    assert values["served"] == "yes" and values["RESULT"] == "expected"


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
