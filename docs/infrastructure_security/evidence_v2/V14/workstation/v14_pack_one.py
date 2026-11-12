"""Pack one file into a neutral inbound archive for V14 (STEPS.md H08a and H08e-2): metadata out only.

usage:
  py -3.10 v14_pack_one.py --freeze <freeze_bundle worktree> --esr --out-dir <folder> --vars-out <file>
  py -3.10 v14_pack_one.py --freeze <freeze_bundle worktree> --root <private root>
                           --register <register path, relative to the root> --out-dir <folder> --vars-out <file>

--esr packs the ESR record from `git show <tag>:<path>` (V14-OP1: it travels only after the freeze),
and refuses unless its sha256 is the one supplement.json records. --register packs the re-rendered
register of route (ii) (V14-OP9), which must lie under the root at a private/.../fidelity_register_*.json
path. Either way the archive holds that one file at its repository or root-relative path, with a fixed
mtime and owner. The output folder lies outside every worktree (and outside the root).

It prints the archive's neutral name, size and sha256 and the member's sha256, writes <name>.sha256
beside the archive, and writes --vars-out: the PO_ values deploy/aws/scripts/host-run.ps1 sends to
host/v14_inbound.sh. It prints no content.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import secrets
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUPPLEMENT = json.loads((HERE.parent / "supplement.json").read_text(encoding="utf-8"))
TAG = SUPPLEMENT["source"]["tag"]
REVISION = SUPPLEMENT["source"]["revision"]
ESR = SUPPLEMENT["not_in_this_archive"][0]
MTIME = 1767225600  # 2026-01-01T00:00:00Z, fixed
REGISTER = re.compile(r"private/[^/]+/fidelity_register_[^/]+\.json")


def refuse(msg: str) -> None:
    print(f"REFUSED: {msg}")
    print("RESULT=refused")
    sys.exit(1)


def git(freeze: Path, *args: str, binary: bool = False):
    r = subprocess.run(["git", "-C", str(freeze), *args], capture_output=True)
    if r.returncode:
        refuse(f"git {args[0]} failed (exit {r.returncode})")
    return r.stdout if binary else r.stdout.decode().strip()


def inside(child: Path, parent: Path) -> bool:
    return child == parent or child.is_relative_to(parent)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", type=Path, required=True)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--esr", action="store_true")
    what.add_argument("--register")
    ap.add_argument("--root", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--vars-out", type=Path, required=True)
    a = ap.parse_args()
    freeze, out = a.freeze.resolve(), a.out_dir.resolve()

    if git(freeze, "rev-parse", f"{TAG}^{{commit}}") != REVISION:
        refuse("the tag does not name the O5 revision")
    trees = [Path(l.split(" ", 1)[1]).resolve() for l in
             git(freeze, "worktree", "list", "--porcelain").splitlines() if l.startswith("worktree ")]
    if any(inside(out, t) for t in trees):
        refuse("the output folder lies inside a worktree of the repository")

    if a.esr:
        rel, kind = ESR["path"], "esr"
        data = git(freeze, "show", f"{TAG}:{rel}", binary=True)
        if not ESR.get("sha256") or hashlib.sha256(data).hexdigest() != ESR["sha256"]:
            refuse("the ESR record at the tag does not match supplement.json")
    else:
        if a.root is None:
            refuse("--register needs --root")
        root = a.root.resolve()
        if any(inside(root, t) for t in trees):
            refuse("the private root lies inside a worktree of the repository")
        if inside(out, root):
            refuse("the output folder lies inside the private root")
        rel, kind = a.register.replace("\\", "/"), "register"
        if not REGISTER.fullmatch(rel):
            refuse("the register path is not private/<folder>/fidelity_register_<revision>.json")
        path = (root / rel).resolve()
        if not inside(path, root) or not path.is_file():
            refuse("the register is not a file under the root")
        data = path.read_bytes()
    print(f"kind={kind} tag={TAG}")

    name = f"input-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3)}.tar.gz"
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        info = tarfile.TarInfo(rel)
        info.size, info.mtime, info.mode = len(data), MTIME, 0o600
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        tar.addfile(info, io.BytesIO(data))
    gz = io.BytesIO()
    with gzip.GzipFile(fileobj=gz, mode="wb", mtime=MTIME, filename="") as g:
        g.write(raw.getvalue())
    out.mkdir(parents=True, exist_ok=True)
    archive = out / name
    archive.write_bytes(gz.getvalue())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    member = hashlib.sha256(data).hexdigest()
    (out / f"{name}.sha256").write_text(f"{digest}  {name}\n", encoding="ascii", newline="\n")
    a.vars_out.write_text(json.dumps({"PO_KIND": kind, "PO_ARCHIVE": name, "PO_ARCHIVE_SHA256": digest,
                                      "PO_MEMBER_SHA256": member}, indent=2) + "\n",
                          encoding="utf-8", newline="\n")
    print(f"archive_name={name}")
    print(f"archive_bytes={archive.stat().st_size}")
    print(f"archive_sha256={digest}")
    print(f"member_sha256={member}")
    print(f"vars_out={a.vars_out.name}")
    print("RESULT=packed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
