#!/usr/bin/env bash
# Rerun the bundle-only chain; each time a file under the root is "not found", copy it from the tag.
# usage: fill_loop.sh <bundle_only> <pristine root> <work root> <traces> <tag>
set -u
B=$1; PRISTINE=$2; WORK=$3; TR=$4; TAG=$5
BIN=$(dirname "$0")
WIN=$(cygpath -w "$WORK")
: > "$TR/supplement.txt"
for i in $(seq 1 25); do
  # keep the supplement, reset everything the chain writes
  rm -rf "$WORK.keep"; mkdir -p "$WORK.keep"
  while read -r f; do [ -n "$f" ] && mkdir -p "$WORK.keep/$(dirname "$f")" && cp "$WORK/$f" "$WORK.keep/$f"; done < "$TR/supplement.txt"
  rm -rf "$WORK"; cp -r "$PRISTINE" "$WORK"; cp -r "$WORK.keep/." "$WORK/"
  rm -f "$TR"/bo_*
  USE_REPO_ROOT=1 bash "$BIN/rehearse_s5.sh" "$B" "$WORK" "$TR" bo > "$TR/loop_$i.txt" 2>&1
  missing=$(cat "$TR"/bo_*.out 2>/dev/null | grep -o "not found: [^ ]*" | head -1 | sed 's/^not found: //')
  if [ -z "$missing" ]; then echo "iteration $i: no missing file"; cat "$TR/loop_$i.txt"; break; fi
  rel=$(py -3.10 -c "import sys,pathlib;print(pathlib.PureWindowsPath(sys.argv[1]).relative_to(pathlib.PureWindowsPath(sys.argv[2])).as_posix())" "$missing" "$WIN")
  echo "iteration $i: missing $rel"
  mkdir -p "$WORK/$(dirname "$rel")"
  (cd /c/Code/proposal_demo/freeze_bundle && git show "$TAG:$rel" > "$WORK/$rel") || { echo "not at tag: $rel"; break; }
  echo "$rel" >> "$TR/supplement.txt"
done
