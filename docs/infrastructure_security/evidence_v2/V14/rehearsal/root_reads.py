"""Union of private-root files opened by the given traces, relative to the root named by argv[1]."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
seen = set()
for f in sys.argv[2:]:
    for p in json.loads(Path(f).read_text(encoding="utf-8"))["opened_outside_tree"]:
        q = Path(p)
        if q.is_relative_to(root):
            seen.add(q.relative_to(root).as_posix())
for p in sorted(seen):
    print(p)
