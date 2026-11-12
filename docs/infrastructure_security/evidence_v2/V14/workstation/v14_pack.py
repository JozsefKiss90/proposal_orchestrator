"""Build V14's inbound archive on the workstation: metadata out, no content shown.

usage:
  py -3.10 v14_pack.py --freeze <freeze_bundle worktree> --root <private root>
                       --config-input <configuration input, relative to the root>
                       --out-dir <folder outside the root and every checkout>

What it does, in order, refusing at the first failure:
  1. The freeze worktree is clean and at the O5 revision, and the tag names it.
  2. The private root and the output folder lie outside every worktree of the
     repository, and the output folder lies outside the root.
  3. Each supplement file (supplement.json, beside this script) is written into
     the root at its repository path from `git show <tag>:<path>`, and its
     sha256 is checked. A file already there with other bytes is refused.
  4. No ESR record is anywhere under the root.
  5. The archive holds the workspace, every revision's register and the
     supplement, and nothing else: no PDF, no dry-import record, no
     configuration input (REHEARSAL.md, R6). Members are sorted, with a fixed
     mtime and owner, so the same inputs give the same bytes.
  6. It prints the archive's neutral name, size, sha256 and member counts, and
     writes <name>.sha256 beside it. It prints no member path.

The bytes shipped come from the tag. This script only selects and packs them.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
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
ESR_NAME = Path(SUPPLEMENT["not_in_this_archive"][0]["path"]).name
MTIME = 1767225600  # 2026-01-01T00:00:00Z, fixed


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
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--config-input", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    freeze, root, out = a.freeze.resolve(), a.root.resolve(), a.out_dir.resolve()

    # 1
    if git(freeze, "rev-parse", "HEAD") != REVISION:
        refuse("the freeze worktree is not at the O5 revision")
    if git(freeze, "rev-parse", f"{TAG}^{{commit}}") != REVISION:
        refuse("the tag does not name the O5 revision")
    if git(freeze, "status", "--porcelain", "--untracked-files=no"):
        refuse("the freeze worktree has tracked changes")
    print(f"freeze_revision={REVISION} tag={TAG} clean=yes")

    # 2
    trees = [Path(l.split(" ", 1)[1]).resolve() for l in
             git(freeze, "worktree", "list", "--porcelain").splitlines() if l.startswith("worktree ")]
    for t in trees:
        if inside(root, t) or inside(out, t):
            refuse("the private root or the output folder lies inside a worktree of the repository")
    if inside(out, root):
        refuse("the output folder lies inside the private root")
    print(f"worktrees_checked={len(trees)} root_outside=yes out_outside=yes")

    # 3
    for f in SUPPLEMENT["files"]:
        blob = git(freeze, "show", f"{TAG}:{f['path']}", binary=True)
        if hashlib.sha256(blob).hexdigest() != f["sha256"]:
            refuse("a supplement file at the tag does not match supplement.json")
        dest = root / f["path"]
        if dest.exists():
            if hashlib.sha256(dest.read_bytes()).hexdigest() != f["sha256"]:
                refuse("a supplement path in the root already holds other bytes")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
    print(f"supplement_files={len(SUPPLEMENT['files'])} sha256_ok=yes")

    # 4
    if any(p.name == ESR_NAME for p in root.rglob("*")):
        refuse("an ESR record is under the root; it travels only after the freeze (V14-OP1)")
    print("esr_under_root=no")

    # 5
    cfg_path = root / a.config_input
    if not inside(cfg_path.resolve(), root):
        refuse("the configuration input is not under the root")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    workspace = root / cfg["workspace_rel"]
    registers = [root / r["register_rel"] for r in cfg["revisions"]]
    if not workspace.is_dir() or not all(r.is_file() for r in registers):
        refuse("the workspace or a register is missing; run the import first")
    members = sorted({p for p in workspace.rglob("*") if p.is_file()}
                     | set(registers)
                     | {root / f["path"] for f in SUPPLEMENT["files"]})
    for p in members:
        if p.suffix.lower() == ".pdf" or "dry_import" in p.relative_to(root).as_posix():
            refuse("a PDF or a dry-import record would enter the archive")
    name = f"input-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3)}.tar.gz"
    out.mkdir(parents=True, exist_ok=True)
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for p in members:
            data = p.read_bytes()
            info = tarfile.TarInfo(p.relative_to(root).as_posix())
            info.size, info.mtime, info.mode = len(data), MTIME, 0o600
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    gz = io.BytesIO()
    with gzip.GzipFile(fileobj=gz, mode="wb", mtime=MTIME, filename="") as g:
        g.write(raw.getvalue())
    archive = out / name
    archive.write_bytes(gz.getvalue())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (out / f"{name}.sha256").write_text(f"{digest}  {name}\n", encoding="ascii", newline="\n")

    # 6
    n_ws = sum(1 for p in members if inside(p, workspace))
    print(f"archive_name={name}")
    print(f"archive_bytes={archive.stat().st_size}")
    print(f"archive_sha256={digest}")
    print(f"members={len(members)} workspace={n_ws} registers={len(registers)} "
          f"supplement={len(SUPPLEMENT['files'])}")
    print("RESULT=packed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
