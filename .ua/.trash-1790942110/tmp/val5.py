# -*- coding: utf-8 -*-
import json, os, re
OUT = r"C:/Code/proposal_demo/proposal_orchestrator/.ua/intermediate"
META = json.load(open(os.path.join(OUT, "batchmeta", "batch-5-meta.json")))
BID = META["batchImportData"]
NEI = META["neighborMap"]

allowed_file_paths = set(BID.keys())
for v in BID.values():
    allowed_file_paths.update(v)
allowed_sym = set()
for f, nbs in NEI.items():
    for nb in nbs:
        allowed_file_paths.add(nb["path"])
        for s in nb["symbols"]:
            allowed_sym.add((nb["path"], s))

VALID_TYPES = {"file","function","class","config","document","service","table",
               "endpoint","pipeline","schema","resource"}
VALID_EDGES = {"contains","imports","calls","inherits","implements","exports",
               "depends_on","tested_by","configures","documents","deploys",
               "migrates","triggers","defines_schema","serves","provisions",
               "routes","related"}

all_ids = set()
errs = []
parts = []
for k in (1,2,3):
    p = os.path.join(OUT, "batch-5-part-%d.json" % k)
    d = json.load(open(p, encoding="utf-8"))
    parts.append((k, p, d))
    for n in d["nodes"]:
        all_ids.add(n["id"])

imports_count = 0
for k, p, d in parts:
    ids = set(n["id"] for n in d["nodes"])
    for n in d["nodes"]:
        for f in ("id","type","name","summary","tags","complexity"):
            if not n.get(f): errs.append("part%d node %s missing %s" % (k, n.get("id"), f))
        if n["type"] not in VALID_TYPES: errs.append("part%d bad type %s" % (k, n["type"]))
        if not (3 <= len(n["tags"]) <= 5): errs.append("part%d tags count %s %d" % (k, n["id"], len(n["tags"])))
        if n["complexity"] not in ("simple","moderate","complex"): errs.append("part%d bad complexity %s" % (k, n["id"]))
        if n["type"] in ("function","class") and "lineRange" not in n: errs.append("part%d no lineRange %s" % (k, n["id"]))
    for e in d["edges"]:
        if e["type"] == "imports": imports_count += 1
        if e["type"] not in VALID_EDGES: errs.append("part%d bad edge type %s" % (k, e["type"]))
        if e["direction"] != "forward": errs.append("part%d bad direction" % k)
        if e["source"] == e["target"]: errs.append("part%d self edge %s" % (k, e["source"]))
        if e["source"] not in ids: errs.append("part%d source not in part: %s" % (k, e["source"]))
        for side in ("source","target"):
            ref = e[side]
            if ref in all_ids: continue
            m = re.match(r"^file:(.+)$", ref)
            if m and m.group(1) in allowed_file_paths: continue
            m = re.match(r"^(function|class):(.+?):([^:]+)$", ref)
            if m and (m.group(2), m.group(3)) in allowed_sym: continue
            errs.append("part%d unresolved %s %s (edge %s)" % (k, side, ref, e["type"]))

expected_imports = sum(len(v) for v in BID.values())
if imports_count != expected_imports:
    errs.append("imports %d != expected %d" % (imports_count, expected_imports))

print("imports:", imports_count, "/", expected_imports)
print("total nodes:", len(all_ids))
if errs:
    print("ERRORS (%d):" % len(errs))
    for e in errs[:40]: print(" -", e)
else:
    print("VALIDATION OK")
