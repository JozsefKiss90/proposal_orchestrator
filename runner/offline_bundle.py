"""The offline deployment bundle for the private host (AN12, ADR-001 Decision 8).

AN12 of ``.scratch/msca-dn-anonymisation/tickets.md``. The private host has no
internet route, so software reaches it only as one tarball carried through the
S3 gateway endpoint. This module builds that tarball on the operator's
workstation and verifies the installed tree on the host.

Why the bundle carries its own interpreter
------------------------------------------
The host's system Python is 3.9.25. PyMuPDF 1.28.2, the extraction pin of
:mod:`runner.extraction_environment`, publishes no wheel for 3.9, and the
newest build that does (1.26.5) was never measured. So the bundle carries a
relocatable CPython from python-build-standalone, at a version the pin was
measured on. The operator chose this on 2026-10-16; the decision record is
``msca-dn-an12-offline-bundle_2026-10-16``.

What :func:`build` puts in the tarball
--------------------------------------
Under one top directory named for the bundle:

``app/``
    every file of the spec's roots **as committed at HEAD**, read from git
    blobs. Working-tree edits, untracked files and line-ending conversion
    never reach the host. ``app/.git`` is an empty directory, the marker
    :func:`runner.paths.find_repo_root` needs. ``app/bundle_manifest.json``
    binds every file by hash, with the revision it came from.
``wheels/``
    exactly the wheels ``deploy/requirements-host.txt`` pins, each matched by
    hash and checked against the host's interpreter, machine and glibc.
``python/``
    the interpreter archive, unextracted, matched against the spec's hash.
``SHA256SUMS``
    the interpreter and every wheel, so the host can check them with
    ``sha256sum -c`` before it runs anything from the bundle.

Two builds of one commit with the same inputs are byte-equal: entries are
sorted, owners are zero, every timestamp is the commit's, and the gzip header
carries none.

What :func:`verify` checks on the host
--------------------------------------
:data:`CHECKS`: the installed files against the manifest, the interpreter and
glibc, the extraction pin, every installed distribution's version, the four
ADR-001 environment controls, that the Bedrock runtime endpoint resolves only
to private addresses (the VPC endpoint, ADR-001 DC-02), and, when asked, that
an internet endpoint is unreachable. An unprobed route is not a pass, and nor
is a probe whose name did not resolve: that measures DNS, not the route. The record holds versions,
hashes and the checked settings only, never another environment value.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import ipaddress
import json
import os
import platform
import re
import socket
import subprocess
import sys
import tarfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from runner import extraction_environment as ee
from runner.atomic_write import atomic_write_text, canonical_json_bytes

SPEC_SCHEMA = "offline_bundle_spec/1"
MANIFEST_SCHEMA = "offline_bundle_manifest/1"
MANIFEST_RECORD_TYPE = "offline_bundle_manifest"
VERIFICATION_SCHEMA = "offline_bundle_verification/1"
VERIFICATION_RECORD_TYPE = "offline_bundle_verification"

#: The committed spec, repository-relative.
SPEC_REL = "deploy/offline_bundle.json"
MANIFEST_FILE = "bundle_manifest.json"
CHECKSUM_FILE = "SHA256SUMS"

#: Every check :func:`verify` reports, in order.
CHECKS: tuple[str, ...] = (
    "files",
    "interpreter",
    "glibc",
    "extraction_pin",
    "distributions",
    "production_mode",
    "diagnostic_level",
    "transport",
    "region",
    "private_endpoint",
    "no_internet_route",
)

#: The one transport the host may use (ADR-001 Decisions 2 and 9).
HOST_BACKEND = "bedrock_converse"

_REQUIREMENT = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)==(?P<version>[^\s;=]+)\s+"
    r"--hash=sha256:(?P<sha>[0-9a-f]{64})$"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MANYLINUX_LEGACY = {"manylinux1": (2, 5), "manylinux2010": (2, 12), "manylinux2014": (2, 17)}
_MANYLINUX = re.compile(r"^manylinux_(\d+)_(\d+)_(\w+)$")
_LEGACY = re.compile(r"^(manylinux1|manylinux2010|manylinux2014)_(\w+)$")
_SPEC_FIELDS = ("schema", "bundle_name", "interpreter", "target", "requirements", "roots")
_INTERPRETER_FIELDS = ("python_version", "archive", "sha256")
_TARGET_FIELDS = ("python_tag", "machine", "glibc")


class BundleRefused(RuntimeError):
    """The bundle cannot be built or read as asked. Nothing was written."""


def normalise(name: str) -> str:
    """A distribution name as PEP 503 compares it."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:2])


# --------------------------------------------------------------------------- #
# Requirements and wheels
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Requirement:
    name: str
    version: str
    sha256: str


def parse_requirements(text: str) -> list[Requirement]:
    """Every pin of a host requirements file. Anything but ``name==version --hash=sha256:...``
    on one line is refused: the host installs in hash-checking mode, from these pins alone."""
    out: list[Requirement] = []
    seen: set[str] = set()
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _REQUIREMENT.match(line)
        if match is None:
            raise BundleRefused(
                f"requirements line {number} is not an exact pin with one sha256 hash: {line!r}"
            )
        name = normalise(match["name"])
        if name in seen:
            raise BundleRefused(f"requirements name {name} twice")
        seen.add(name)
        out.append(Requirement(name, match["version"], match["sha"]))
    return out


@dataclass(frozen=True)
class Target:
    """The host's interpreter tag, machine and glibc."""

    python_tag: str
    machine: str
    glibc: str

    @property
    def minor(self) -> int:
        return int(self.python_tag[3:])

    @property
    def glibc_version(self) -> tuple[int, ...]:
        return _version(self.glibc)


@dataclass(frozen=True)
class Wheel:
    file: str
    name: str
    version: str
    python_tags: tuple[str, ...]
    abi_tags: tuple[str, ...]
    platform_tags: tuple[str, ...]

    def _platforms(self, target: Target) -> list[Optional[tuple[int, int]]]:
        """The glibc each tag that suits *target*'s machine needs; ``None`` for ``any``."""
        found: list[Optional[tuple[int, int]]] = []
        for tag in self.platform_tags:
            if tag == "any":
                found.append(None)
                continue
            modern, legacy = _MANYLINUX.match(tag), _LEGACY.match(tag)
            if modern and modern[3] == target.machine:
                found.append((int(modern[1]), int(modern[2])))
            elif legacy and legacy[2] == target.machine:
                found.append(_MANYLINUX_LEGACY[legacy[1]])
        return found

    def glibc_needed(self, target: Target) -> Optional[tuple[int, int]]:
        """The oldest glibc any of this wheel's tags runs on, or ``None`` if it needs none."""
        found = self._platforms(target)
        if not found or None in found:
            return None
        return min(v for v in found if v is not None)


def parse_wheel(filename: str) -> Wheel:
    if not filename.endswith(".whl"):
        raise BundleRefused(f"{filename!r} is not a wheel")
    parts = filename[: -len(".whl")].split("-")
    if len(parts) not in (5, 6):
        raise BundleRefused(f"{filename!r} is not a wheel file name")
    name, version = parts[0], parts[1]
    py, abi, plat = parts[-3:]
    return Wheel(filename, normalise(name), version, tuple(py.split(".")),
                 tuple(abi.split(".")), tuple(plat.split(".")))


def _interpreter_fits(wheel: Wheel, target: Target) -> bool:
    for py in wheel.python_tags:
        for abi in wheel.abi_tags:
            if abi == "none" and py in ("py3", f"py3{target.minor}", target.python_tag):
                return True
            if abi == "abi3" and py.startswith("cp3") and py[3:].isdigit() and int(py[3:]) <= target.minor:
                return True
            if abi == py == target.python_tag:
                return True
    return False


def wheel_problem(wheel: Wheel, target: Target) -> Optional[str]:
    """Why the host cannot run *wheel*, or ``None`` when it can."""
    if not _interpreter_fits(wheel, target):
        return (f"{wheel.file}: built for interpreter tags "
                f"{'.'.join(wheel.python_tags)}-{'.'.join(wheel.abi_tags)}, not {target.python_tag}")
    found = wheel._platforms(target)
    if not found:
        return (f"{wheel.file}: platform {'.'.join(wheel.platform_tags)} is not "
                f"manylinux {target.machine} or any")
    needed = wheel.glibc_needed(target)
    if needed is not None and needed > target.glibc_version:
        return (f"{wheel.file}: needs glibc {needed[0]}.{needed[1]}, newer than the "
                f"target's {target.glibc}")
    return None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_wheels(requirements: Sequence[Requirement], wheel_dir: Path,
                 target: Target) -> list[dict[str, str]]:
    """The wheel records for the manifest, refused unless *wheel_dir* holds exactly one
    runnable wheel per pin, each matching its pinned hash. Every problem is named at once."""
    pinned = {r.name: r for r in requirements}
    problems: list[str] = []
    records: list[dict[str, str]] = []
    found: dict[str, str] = {}
    for path in sorted(Path(wheel_dir).glob("*.whl")):
        wheel = parse_wheel(path.name)
        req = pinned.get(wheel.name)
        if req is None or req.version != wheel.version:
            problems.append(f"{path.name}: not pinned by the requirements")
            continue
        if wheel.name in found:
            problems.append(f"{path.name}: a second wheel for {wheel.name} ({found[wheel.name]})")
            continue
        found[wheel.name] = path.name
        sha = _file_sha256(path)
        if sha != req.sha256:
            problems.append(f"{path.name}: hash {sha} is not the pinned {req.sha256}")
        problem = wheel_problem(wheel, target)
        if problem:
            problems.append(problem)
        records.append({"file": path.name, "name": wheel.name, "version": wheel.version,
                        "sha256": sha})
    for name, req in pinned.items():
        if name not in found:
            problems.append(f"{name}=={req.version}: no wheel in {Path(wheel_dir).name}")
    if problems:
        raise BundleRefused("the wheel set does not match the requirements:\n  "
                            + "\n  ".join(problems))
    return records


# --------------------------------------------------------------------------- #
# The spec
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Spec:
    record: dict[str, Any]
    sha256: str
    bundle_name: str
    interpreter: dict[str, Any]
    target: Target
    requirements: str
    roots: tuple[str, ...]


def _relative(path: Any, what: str) -> str:
    if not isinstance(path, str) or not path:
        raise BundleRefused(f"{what} is not a repository-relative path")
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or "\\" in path or str(pure) != path:
        raise BundleRefused(f"{what} {path!r} is not a plain repository-relative path")
    return path


def load_spec(data: bytes) -> Spec:
    try:
        record = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BundleRefused(f"the bundle spec is not JSON: {exc}") from exc
    if not isinstance(record, dict) or record.get("schema") != SPEC_SCHEMA:
        raise BundleRefused(f"the bundle spec is not an {SPEC_SCHEMA} record")
    missing = [f for f in _SPEC_FIELDS if f not in record]
    interpreter, target = record.get("interpreter"), record.get("target")
    if isinstance(interpreter, dict):
        missing += [f"interpreter.{f}" for f in _INTERPRETER_FIELDS if not interpreter.get(f)]
    if isinstance(target, dict):
        missing += [f"target.{f}" for f in _TARGET_FIELDS if not target.get(f)]
    if missing or not isinstance(interpreter, dict) or not isinstance(target, dict):
        raise BundleRefused(f"the bundle spec lacks {missing or ['interpreter', 'target']}")
    if not _SHA256.match(str(interpreter["sha256"])):
        raise BundleRefused("the bundle spec's interpreter hash is not a sha256")
    if not re.match(r"^cp3\d+$", str(target["python_tag"])):
        raise BundleRefused(f"target.python_tag {target['python_tag']!r} is not a CPython tag")
    roots = record["roots"]
    if not isinstance(roots, list) or not roots:
        raise BundleRefused("the bundle spec names no roots")
    return Spec(
        record=record,
        sha256=hashlib.sha256(data).hexdigest(),
        bundle_name=_relative(record["bundle_name"], "bundle_name"),
        interpreter=interpreter,
        target=Target(str(target["python_tag"]), str(target["machine"]), str(target["glibc"])),
        requirements=_relative(record["requirements"], "requirements"),
        roots=tuple(_relative(r, "root") for r in roots),
    )


def covered(path: str, roots: Iterable[str]) -> bool:
    """Whether repository path *path* lies in one of *roots*."""
    return any(path == root or path.startswith(root + "/") for root in roots)


# --------------------------------------------------------------------------- #
# Git: the committed bytes
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str, stdin: Optional[bytes] = None) -> bytes:
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], input=stdin, capture_output=True,
                              check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", b"") or b""
        raise BundleRefused(f"git {' '.join(args[:2])} failed: "
                            f"{stderr.decode('utf-8', 'replace').strip() or exc}") from exc
    return done.stdout


def _committed(repo: Path, path: str) -> bytes:
    return _git(repo, "cat-file", "blob", f"HEAD:{path}")


@dataclass(frozen=True)
class _Entry:
    path: str
    mode: int
    data: bytes


def _committed_tree(repo: Path, roots: Sequence[str]) -> list[_Entry]:
    listing = _git(repo, "ls-tree", "-r", "-z", "--full-tree", "HEAD", "--", *roots)
    rows: list[tuple[str, str, str]] = []
    for item in listing.split(b"\0"):
        if not item:
            continue
        meta, path = item.decode("utf-8").split("\t", 1)
        mode, kind, obj = meta.split(" ")
        if kind != "blob":
            raise BundleRefused(f"{path} is a {kind}, not a file; a bundle carries files only")
        rows.append((path, mode, obj))
    unmatched = [r for r in roots if not any(covered(path, [r]) for path, _m, _o in rows)]
    if unmatched:
        raise BundleRefused(f"no committed file lies under the spec's roots {unmatched}")
    batch = _git(repo, "cat-file", "--batch", stdin=b"".join(f"{o}\n".encode() for _p, _m, o in rows))
    entries: list[_Entry] = []
    offset = 0
    for path, mode, obj in rows:
        header_end = batch.index(b"\n", offset)
        sha, _kind, size = batch[offset:header_end].decode().split(" ")
        if sha != obj:  # pragma: no cover - git answers in order
            raise BundleRefused(f"git answered {sha} for {path}, not {obj}")
        start = header_end + 1
        entries.append(_Entry(path, 0o755 if mode == "100755" else 0o644,
                              batch[start:start + int(size)]))
        offset = start + int(size) + 1
    return sorted(entries, key=lambda e: e.path)


# --------------------------------------------------------------------------- #
# The build
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class BuildResult:
    tarball: Path
    tarball_sha256: str
    manifest: dict[str, Any]


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _info(name: str, size: int, mtime: int, mode: int = 0o644,
          kind: bytes = tarfile.REGTYPE) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size, info.mtime, info.mode, info.type = size, mtime, mode, kind
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def build(*, repo_root: Path, spec_path: Path, wheel_dir: Path, interpreter: Path,
          out_dir: Path) -> BuildResult:
    """Build the bundle from HEAD of *repo_root* under the spec at *spec_path*.

    The spec and the requirements are read as committed, so the manifest
    describes the commit it names. Every refusal runs before anything is
    written.
    """
    repo_root, out_dir = Path(repo_root).resolve(), Path(out_dir).resolve()
    if _inside(out_dir, repo_root):
        raise BundleRefused(f"the output directory {out_dir} is inside the repository; a "
                            f"bundle is built outside the tree it packages")
    try:
        spec_rel = Path(spec_path).resolve().relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise BundleRefused(f"the spec {spec_path} is not inside the repository it packages") from exc
    spec = load_spec(_committed(repo_root, spec_rel))
    minor = ".".join(str(spec.interpreter["python_version"]).split(".")[:2])
    if minor not in ee.MEASURED_PYTHON:
        raise BundleRefused(f"interpreter {spec.interpreter['python_version']} is not one the "
                            f"extraction pin was measured on ({', '.join(ee.MEASURED_PYTHON)})")
    if spec.target.python_tag != "cp" + minor.replace(".", ""):
        raise BundleRefused(f"target {spec.target.python_tag} is not the interpreter's {minor}")
    if not covered(spec.requirements, spec.roots):
        raise BundleRefused(f"the requirements {spec.requirements} lie outside the spec's roots, "
                            f"so the host could not install from them")
    requirements_bytes = _committed(repo_root, spec.requirements)
    requirements = parse_requirements(requirements_bytes.decode("utf-8"))
    pins = {r.name: r.version for r in requirements}
    if pins.get("pymupdf") != ee.PINNED_PYMUPDF:
        raise BundleRefused(f"the requirements pin pymupdf {pins.get('pymupdf')}, not the "
                            f"extraction pin {ee.PINNED_PYMUPDF}")
    interpreter = Path(interpreter)
    interpreter_sha = _file_sha256(interpreter)
    if interpreter_sha != spec.interpreter["sha256"]:
        raise BundleRefused(f"the interpreter archive {interpreter.name} hashes to "
                            f"{interpreter_sha}, not the pinned {spec.interpreter['sha256']}")
    wheels = check_wheels(requirements, Path(wheel_dir), spec.target)
    needs = [parse_wheel(w["file"]).glibc_needed(spec.target) for w in wheels]
    glibc = max((n for n in needs if n is not None), default=None)

    revision = _git(repo_root, "rev-parse", "HEAD").decode().strip()
    mtime = int(_git(repo_root, "show", "-s", "--format=%ct", "HEAD").decode().strip())
    entries = _committed_tree(repo_root, spec.roots)
    archive = str(spec.interpreter["archive"])
    manifest: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        "record_type": MANIFEST_RECORD_TYPE,
        "bundle_name": spec.bundle_name,
        "repository_revision": revision,
        "committed_at": mtime,
        "spec": {"path": spec_rel, "sha256": spec.sha256},
        "requirements": {"path": spec.requirements,
                         "sha256": hashlib.sha256(requirements_bytes).hexdigest()},
        "interpreter": {"archive": archive, "sha256": interpreter_sha,
                        "python_version": spec.interpreter["python_version"]},
        "target": spec.record["target"],
        "glibc_required": None if glibc is None else f"{glibc[0]}.{glibc[1]}",
        "extraction_pin": {"pymupdf": ee.PINNED_PYMUPDF, "mupdf": ee.PINNED_MUPDF},
        "wheels": wheels,
        "file_count": len(entries),
        "files": [{"path": e.path, "sha256": hashlib.sha256(e.data).hexdigest(),
                   "size": len(e.data)} for e in entries],
    }
    manifest_bytes = canonical_json_bytes(manifest)
    sums = "".join(f"{sha}  {path}\n" for path, sha in
                   [(f"python/{archive}", interpreter_sha)]
                   + [(f"wheels/{w['file']}", w["sha256"]) for w in wheels]).encode()

    top = spec.bundle_name
    out_dir.mkdir(parents=True, exist_ok=True)
    tarball = out_dir / f"{top}.tar.gz"
    partial = out_dir / f".{top}.tar.gz.partial"
    with partial.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for entry in entries:
                    tar.addfile(_info(f"{top}/app/{entry.path}", len(entry.data), mtime,
                                      entry.mode), io.BytesIO(entry.data))
                tar.addfile(_info(f"{top}/app/.git", 0, mtime, 0o755, tarfile.DIRTYPE))
                tar.addfile(_info(f"{top}/app/{MANIFEST_FILE}", len(manifest_bytes), mtime),
                            io.BytesIO(manifest_bytes))
                with interpreter.open("rb") as handle:
                    tar.addfile(_info(f"{top}/python/{archive}", interpreter.stat().st_size,
                                      mtime), handle)
                for w in wheels:
                    path = Path(wheel_dir) / w["file"]
                    with path.open("rb") as handle:
                        tar.addfile(_info(f"{top}/wheels/{w['file']}", path.stat().st_size,
                                          mtime), handle)
                tar.addfile(_info(f"{top}/{CHECKSUM_FILE}", len(sums), mtime), io.BytesIO(sums))
    os.replace(partial, tarball)
    tarball_sha = _file_sha256(tarball)
    atomic_write_text(f"{tarball_sha}  {tarball.name}\n", out_dir / f"{tarball.name}.sha256")
    atomic_write_text(manifest_bytes.decode("utf-8"), out_dir / MANIFEST_FILE)
    return BuildResult(tarball, tarball_sha, manifest)


# --------------------------------------------------------------------------- #
# The host verification
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class HostFacts:
    """What the running host is, measured once."""

    python_version: str
    machine: str
    libc: tuple[str, str]
    extraction: Optional[ee.Environment]
    distributions: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def measure(cls, names: Iterable[str]) -> "HostFacts":
        from importlib import metadata

        try:
            extraction: Optional[ee.Environment] = ee.measure()
        except ImportError:
            extraction = None
        found: dict[str, str] = {}
        for name in names:
            try:
                found[normalise(name)] = metadata.version(name)
            except metadata.PackageNotFoundError:
                pass
        libc_name, libc_version = platform.libc_ver()
        return cls(platform.python_version(), platform.machine(), (libc_name, libc_version),
                   extraction, found)


def _check(name: str, passed: Optional[bool], detail: str) -> dict[str, Any]:
    return {"check": name, "passed": passed, "detail": detail}


def _files(app_root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    altered, missing = [], []
    for entry in manifest["files"]:
        path = app_root / entry["path"]
        if not path.is_file():
            missing.append(entry["path"])
        elif _file_sha256(path) != entry["sha256"]:
            altered.append(entry["path"])
    if altered or missing:
        return _check("files", False, f"altered: {altered}; missing: {missing}")
    return _check("files", True, f"all {len(manifest['files'])} files match the manifest")


def _transport(environ: Mapping[str, str]) -> dict[str, Any]:
    preset = environ.get("ORCHESTRATOR_TRANSPORT_PRESET")
    explicit = environ.get("ORCHESTRATOR_TRANSPORT_BACKEND")
    if preset:
        from runner.transport.config import get_transport_preset

        try:
            backend = get_transport_preset(preset).backend_name
        except (KeyError, ValueError) as exc:
            return _check("transport", False, f"preset {preset!r} does not resolve: {exc}")
        if explicit is not None and explicit != backend:
            return _check("transport", False, f"backend {explicit!r} conflicts with preset {preset!r}")
        source = f"preset {preset}"
    else:
        backend = explicit or "claude_cli"
        source = "ORCHESTRATOR_TRANSPORT_BACKEND"
    return _check("transport", backend == HOST_BACKEND, f"{source} resolves to {backend}")


def _region_setting(environ: Mapping[str, str]) -> Optional[tuple[str, str]]:
    for var in ("AWS_REGION", "AWS_DEFAULT_REGION"):
        if environ.get(var):
            return var, environ[var]
    return None


def _region(environ: Mapping[str, str]) -> dict[str, Any]:
    from runner.anonymisation_rewrite import ALLOWED_REGIONS

    setting = _region_setting(environ)
    if setting is None:
        return _check("region", False, "neither AWS_REGION nor AWS_DEFAULT_REGION is set")
    var, region = setting
    return _check("region", region in ALLOWED_REGIONS,
                  f"{var}={region}; ADR-001 allows {list(ALLOWED_REGIONS)}")


def _resolve(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    return sorted({str(info[4][0]) for info in infos})


def _private_endpoint(environ: Mapping[str, str]) -> dict[str, Any]:
    from runner.anonymisation_rewrite import ALLOWED_REGIONS

    setting = _region_setting(environ)
    if setting is None or setting[1] not in ALLOWED_REGIONS:
        return _check("private_endpoint", False, "no ADR-001 region to resolve the endpoint in")
    region = setting[1]
    host = f"bedrock-runtime.{region}.amazonaws.com"
    try:
        addresses = _resolve(host)
    except OSError as exc:
        return _check("private_endpoint", False, f"{host} did not resolve ({type(exc).__name__})")
    public = [a for a in addresses if not ipaddress.ip_address(a).is_private]
    return _check("private_endpoint", bool(addresses) and not public,
                  f"{host} resolves to {', '.join(addresses) or 'nothing'}"
                  + (f"; not private: {', '.join(public)}" if public else ""))


def _tcp(host: str, port: int, timeout: float) -> socket.socket:
    return socket.create_connection((host, port), timeout=timeout)


def _probe(probe: Optional[tuple[str, int]], connect: Callable[..., Any]) -> dict[str, Any]:
    if probe is None:
        return _check("no_internet_route", None,
                      "not probed; pass --probe-no-internet HOST:PORT to measure it")
    host, port = probe
    try:
        connection = connect(host, port, 5)
    except socket.gaierror as exc:
        return _check("no_internet_route", None,
                      f"{host} did not resolve ({type(exc).__name__}), so the route was not "
                      "measured; probe an IP address instead")
    except socket.timeout:
        return _check("no_internet_route", True, f"{host}:{port} unreachable (timed out)")
    except OSError as exc:
        return _check("no_internet_route", True,
                      f"{host}:{port} unreachable ({type(exc).__name__})")
    close = getattr(connection, "close", None)
    if close:
        close()
    return _check("no_internet_route", False, f"{host}:{port} accepted a connection")


def verify(app_root: Path, *, environ: Optional[Mapping[str, str]] = None,
           facts: Optional[HostFacts] = None, probe: Optional[tuple[str, int]] = None,
           connect: Callable[..., Any] = _tcp) -> dict[str, Any]:
    """The verification record for the installed tree at *app_root*."""
    app_root = Path(app_root)
    manifest_path = app_root / MANIFEST_FILE
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleRefused(f"{manifest_path} cannot be read: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != MANIFEST_SCHEMA:
        raise BundleRefused(f"{manifest_path} is not an {MANIFEST_SCHEMA} record")
    environ = os.environ if environ is None else environ
    if facts is None:
        facts = HostFacts.measure(w["name"] for w in manifest["wheels"])

    target = manifest["target"]
    wanted_python = manifest["interpreter"]["python_version"]
    interpreter_ok = facts.python_version == wanted_python and facts.machine == target["machine"]
    libc_name, libc_version = facts.libc
    needed = manifest.get("glibc_required")
    glibc_ok = libc_name == "glibc" and bool(libc_version) and (
        needed is None or _version(libc_version) >= _version(needed))
    if facts.extraction is None:
        extraction = _check("extraction_pin", False, "pymupdf does not import")
    else:
        reason = ee.off_pin_reason(facts.extraction)
        extraction = _check("extraction_pin", reason is None,
                            reason or f"PyMuPDF {facts.extraction.pymupdf} with MuPDF "
                                      f"{facts.extraction.mupdf}, on pin")
    wrong = [f"{w['name']} {facts.distributions.get(w['name'], 'absent')} (pinned {w['version']})"
             for w in manifest["wheels"] if facts.distributions.get(w["name"]) != w["version"]]
    production = environ.get("ORCHESTRATOR_PRODUCTION_MODE", "")
    level = environ.get("ORCHESTRATOR_DIAGNOSTIC_LEVEL", "").strip().lower()

    checks = [
        _files(app_root, manifest),
        _check("interpreter", interpreter_ok,
               f"Python {facts.python_version} on {facts.machine}; the bundle carries "
               f"{wanted_python} for {target['machine']}"),
        _check("glibc", glibc_ok, f"{libc_name or 'no libc'} {libc_version or ''}; the wheels "
                                  f"need {needed or 'none'}".replace("  ", " ")),
        extraction,
        _check("distributions", not wrong,
               "; ".join(wrong) or f"all {len(manifest['wheels'])} pinned distributions installed"),
        _check("production_mode", production.lower() == "true",
               f"ORCHESTRATOR_PRODUCTION_MODE={production or '(unset)'}"),
        _check("diagnostic_level", level == "metadata",
               f"ORCHESTRATOR_DIAGNOSTIC_LEVEL={level or '(unset)'}"),
        _transport(environ),
        _region(environ),
        _private_endpoint(environ),
        _probe(probe, connect),
    ]
    return {
        "schema": VERIFICATION_SCHEMA,
        "record_type": VERIFICATION_RECORD_TYPE,
        "bundle_name": manifest["bundle_name"],
        "repository_revision": manifest["repository_revision"],
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "measured": {
            "python": facts.python_version,
            "machine": facts.machine,
            "libc": list(facts.libc),
            "pymupdf": None if facts.extraction is None else facts.extraction.pymupdf,
            "mupdf": None if facts.extraction is None else facts.extraction.mupdf,
        },
        "checks": checks,
        "passed": all(c["passed"] is True for c in checks),
    }


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #


def _endpoint(text: str) -> tuple[str, int]:
    host, sep, port = text.rpartition(":")
    if not sep or not host or not port.isdigit():
        raise argparse.ArgumentTypeError(f"{text!r} is not HOST:PORT")
    return host, int(port)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m runner.offline_bundle",
        description="Build the offline host bundle (workstation) or verify its install (host).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build the bundle from HEAD")
    b.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    b.add_argument("--spec", type=Path, default=None, help=f"default: {SPEC_REL}")
    b.add_argument("--wheels", type=Path, required=True, help="the downloaded wheel directory")
    b.add_argument("--interpreter", type=Path, required=True, help="the interpreter archive")
    b.add_argument("--out-dir", type=Path, required=True, help="outside the repository")
    v = sub.add_parser("verify", help="verify the installed tree on the host")
    v.add_argument("--app-root", type=Path, default=Path(__file__).resolve().parents[1])
    v.add_argument("--probe-no-internet", type=_endpoint, default=None, metavar="HOST:PORT",
                   help="an internet endpoint that must be unreachable, such as pypi.org:443; "
                        "if its name does not resolve, give an IP address")
    v.add_argument("--record", type=Path, default=None, help="also write the record here")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            result = build(repo_root=args.repo_root,
                           spec_path=args.spec or args.repo_root / SPEC_REL,
                           wheel_dir=args.wheels, interpreter=args.interpreter,
                           out_dir=args.out_dir)
            print(f"{result.tarball}\nsha256 {result.tarball_sha256}\n"
                  f"revision {result.manifest['repository_revision']}, "
                  f"{result.manifest['file_count']} files, {len(result.manifest['wheels'])} wheels")
            return 0
        record = verify(args.app_root, probe=args.probe_no_internet)
    except BundleRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    text = canonical_json_bytes(record).decode("utf-8")
    if args.record is not None:
        atomic_write_text(text, args.record)
    print(text)
    return 0 if record["passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
