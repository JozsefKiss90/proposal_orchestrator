"""Print, per trace, the in-tree files opened that the O5 bundle does not hold.
usage: nonbundle.py <bundle_files.txt> <trace.json>..."""
import json
import sys
from pathlib import Path

bundle = {l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip() and "__pycache__" not in l}
print("bundle files:", len(bundle))
union = set()
for f in sys.argv[2:]:
    d = json.loads(Path(f).read_text(encoding="utf-8"))
    extra = [p for p in d["opened_in_tree"] if p not in bundle]
    union.update(extra)
    print(f"{Path(f).stem}: exit={d['exit']} opened_in_tree={len(d['opened_in_tree'])} non_bundle={extra}")
print("UNION:", sorted(union))
