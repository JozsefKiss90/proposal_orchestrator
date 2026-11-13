#!/usr/bin/env python3
"""V14 private diagnosis helper. Use in the interactive session only: the worksheet holds finding and proposal text."""
import datetime, glob, hashlib, json, os, re, sys, textwrap

R = os.environ.get("V14_ROOT", "/root/v14/R")
W = os.path.join(R, "private/msca_dn_original/esr_work")
STATE = os.path.join(W, "diagnosis_state.json")
SHEET = os.path.join(W, "diagnosis_worksheet.txt")
RECORD = os.path.join(W, "diagnosis_private.json")
CATS = ["evidence_omission", "extraction", "rubric_interpretation", "assessor_error",
        "historical_subjectivity", "unresolved_cause"]
STATUSES = ["Confirmed", "Inferred", "Assumed", "Unresolved"]
MISS = "not_detected_despite_sufficient_preserved_evidence"
CONTESTED = ["ESR-E-S03", "ESR-E-S05", "ESR-I-S01", "ESR-I-S02", "ESR-I-S04", "ESR-I-S05", "ESR-Q-S02", "ESR-Q-S03"]
STOP = set(("the and for with that this from are was were has have not but their which will its into than also "
            "been more such each these those they them over under between within about only both does very well "
            "proposal project clearly described").split())


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def save(p, o):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(o, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, p)


def report_path():
    c = [p for p in glob.glob(os.path.join(R, "baseline", "blind_baseline_*.json")) if not p.endswith(".freeze.json")]
    if len(c) != 1:
        sys.exit("expected exactly one baseline report, found %d" % len(c))
    return c[0]


def comparison_path():
    c = sorted(glob.glob(os.path.join(R, "comparisons", "comparison_*_[0-9][0-9][0-9][0-9].json")))
    if not c:
        sys.exit("no comparison found")
    return c[-1]


def toks(t):
    return set(re.findall(r"[a-z][a-z-]{3,}", str(t).lower())) - STOP


def text_of(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return " ".join(text_of(x) for x in v.values())
    if isinstance(v, list):
        return " ".join(text_of(x) for x in v)
    return "" if v is None else str(v)


def findings(rep):
    out = []
    for s in rep["criterion_scoring"]["scores"]:
        for smp in s.get("samples", []):
            for kind, key in (("shortcoming", "shortcomings"), ("strength", "strengths")):
                for i, t in enumerate(smp.get(key, [])):
                    out.append({"criterion": s["criterion_id"], "kind": kind, "sample": smp["sample_index"],
                                "index": i, "text": text_of(t)})
    return out


def top(fs, text, criterion, kind, n=3):
    a = toks(text)
    scored = [(len(a & toks(f["text"])), f) for f in fs if f["criterion"] == criterion and f["kind"] == kind]
    scored.sort(key=lambda x: (-x[0], x[1]["sample"], x[1]["index"]))
    return scored[:n]


def wrap(t, ind="    "):
    return "\n".join(textwrap.wrap(" ".join(str(t).split()), 100, initial_indent=ind, subsequent_indent=ind)) or ind


def cmd_init(force):
    if os.path.exists(STATE) and not force:
        sys.exit("diagnosis_state.json exists. Use: init --force (this discards your answers)")
    rp, cp = report_path(), comparison_path()
    rep, comp = load(rp), load(cp)
    fs = findings(rep)
    scores = {s["criterion_id"]: s for s in rep["criterion_scoring"]["scores"]}
    rows = {r["observation_id"]: r for r in comp["rows"]}
    st = {"bindings": {"report": os.path.relpath(rp, R), "report_sha256": sha(rp),
                       "comparison": os.path.relpath(cp, R), "comparison_sha256": sha(cp)},
          "misses": {}, "false_positives": {}, "deltas": {}, "contested": {}, "avc": {"AVC-01": {}, "AVC-02": {}}}
    L = ["V14 DIAGNOSIS WORKSHEET (private; interactive session only)", "comparison: " + os.path.basename(cp), ""]
    L += ["=" * 100, "A. MISSES - one category each", "=" * 100]
    for oid, r in rows.items():
        if r.get("disposition") != MISS:
            continue
        crit, kind = r["criterion_id"], r["kind"]
        opp = "strength" if kind != "strength" else "shortcoming"
        same = "shortcoming" if opp == "strength" else "strength"
        esr = text_of(r.get("historical_finding"))
        quotes = r.get("current_proposal_evidence") or []
        sc = scores.get(crit, {})
        complete = not sc.get("incompleteness")
        t_opp, t_same = top(fs, esr, crit, opp), top(fs, esr, crit, same)
        best_opp = t_opp[0][0] if t_opp else 0
        hint = "read_and_rated_adequate" if best_opp >= 4 else "absent_from_recorded_output"
        between = (["rubric_interpretation", "historical_subjectivity"] if best_opp >= 4
                   else ["rubric_interpretation", "assessor_error", "historical_subjectivity"])
        st["misses"][oid] = {"kind": kind, "criterion": crit, "category": "unresolved_cause", "between": between,
                             "status": "Assumed", "note": "", "decided_by": "rule",
                             "q2_quote_in_candidate": bool(quotes), "q3_criterion_input_complete": complete,
                             "failure_mode_hint_by_rule": hint}
        L += ["", "%s  [%s, %s]" % (oid, kind, crit), "  ESR says:", wrap(esr)]
        L += ["  Evidence quoted on the row (compare verified it in the extracted candidate):"]
        for q in quotes:
            L += [wrap("[%s] %s" % (q.get("sub_section_id"), q.get("quote")))]
        L += ["  Q2 in extracted candidate: %s    Q3 criterion input complete: %s" %
              ("yes" if quotes else "NO QUOTE ON ROW", "yes" if complete else "NO")]
        L += ["  Closest %ss the assessor wrote (word overlap, sample, index):" % opp]
        for n, f in t_opp:
            L += [wrap("(%d, s%d, i%d) %s" % (n, f["sample"], f["index"], f["text"]))]
        L += ["  Closest %ss the assessor wrote:" % same]
        for n, f in t_same:
            L += [wrap("(%d, s%d, i%d) %s" % (n, f["sample"], f["index"], f["text"]))]
        L += [wrap("Rule default: unresolved_cause between %s (hint: %s)" % (" / ".join(between), hint), "  ")]
    L += ["", "=" * 100, "B. FALSE POSITIVE", "=" * 100]
    fpp = os.path.join(W, "false_positives.txt")
    if os.path.exists(fpp):
        st["false_positives"]["FP-1"] = {"category": "rubric_interpretation", "between": [], "status": "Inferred",
                                         "note": "operator's record in false_positives.txt", "decided_by": "operator"}
        L += [wrap(l, "  ") for l in open(fpp, encoding="utf-8").read().splitlines() if l.strip()]
    L += ["", "=" * 100, "C. CONTESTED STRENGTHS - does the baseline hold a shortcoming on the same point? (yes/no/unclear)",
          "=" * 100]
    for oid in CONTESTED:
        r = rows.get(oid)
        if not r:
            continue
        esr = text_of(r.get("historical_finding"))
        t = top(fs, esr, r["criterion_id"], "shortcoming")
        best = t[0][0] if t else 0
        st["contested"][oid] = {"answer": "unclear", "hint_by_rule": "yes" if best >= 4 else "no", "decided_by": "rule"}
        L += ["", "%s  [%s]  current disposition: %s" % (oid, r["criterion_id"], r.get("disposition")),
              "  ESR praises:", wrap(esr), "  Closest shortcomings the assessor wrote:"]
        for n, f in t:
            L += [wrap("(%d, s%d, i%d) %s" % (n, f["sample"], f["index"], f["text"]))]
        L += ["  Rule hint: %s" % st["contested"][oid]["hint_by_rule"]]
    L += ["", "=" * 100, "D. AVC-01 / AVC-02 - the 5 implementation samples (yes/no/unclear per sample)", "=" * 100,
          "  AVC-01: does the sample claim that no intermediate milestones are shown?",
          "  AVC-02: does the sample credit the deliverables table with the milestones table's verification column?"]
    impl = scores.get("implementation", {})
    for smp in impl.get("samples", []):
        si = str(smp["sample_index"])
        parts = [("shortcoming", x) for x in smp.get("shortcomings", [])] + \
                [("strength", x) for x in smp.get("strengths", [])] + [("rationale", smp.get("rationale", ""))]
        hits = []
        for k, t in parts:
            for sent in re.split(r"(?<=[.;])\s+", text_of(t)):
                if re.search(r"milestone|deliverable", sent, re.I):
                    hits.append((k, sent))
        blob = " ".join(s for _, s in hits)
        a1 = bool(re.search(r"\bno\b[^.]{0,40}milestones?|milestones?[^.]{0,60}\b(not (shown|provided|defined|given|"
                            r"included|specified)|absent|missing|lacking)", blob, re.I))
        a2 = any(re.search(r"deliverable", s, re.I) and re.search(r"milestone", s, re.I) and
                 re.search(r"verif|means of", s, re.I) for _, s in hits)
        st["avc"]["AVC-01"][si] = {"answer": "unclear", "hint_by_rule": "yes" if a1 else "no", "decided_by": "rule"}
        st["avc"]["AVC-02"][si] = {"answer": "unclear", "hint_by_rule": "yes" if a2 else "no", "decided_by": "rule"}
        L += ["", "  sample %s   rule hints: AVC-01 %s, AVC-02 %s" % (si, "yes" if a1 else "no", "yes" if a2 else "no")]
        for k, s in hits:
            L += [wrap("[%s] %s" % (k, s), "      ")]
    L += ["", "=" * 100, "E. CRITERION DELTAS - one category each", "=" * 100]
    for c in scores:
        st["deltas"]["DELTA-" + c] = {"category": "unresolved_cause", "between": [], "status": "Assumed", "note": "",
                                      "decided_by": "rule"}
        L += ["  DELTA-%s   blind score %s" % (c, scores[c].get("score"))]
    save(STATE, st)
    with open(SHEET, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("worksheet: %s" % SHEET)
    cmd_status()


def get_state():
    if not os.path.exists(STATE):
        sys.exit("run init first")
    return load(STATE)


def cmd_status():
    st = get_state()
    for cls in ("misses", "false_positives", "deltas"):
        for k, v in st[cls].items():
            b = (" between " + "+".join(v["between"])) if v.get("between") else ""
            print("%-22s %-24s %-10s %-8s%s" % (k, v["category"], v["status"], v["decided_by"], b))
    for k, v in st["contested"].items():
        print("%-22s answer=%-8s hint=%-4s %s" % (k, v["answer"], v["hint_by_rule"], v["decided_by"]))
    for a in ("AVC-01", "AVC-02"):
        print("%-22s %s" % (a, "  ".join("s%s=%s(%s)" % (i, v["answer"], v["decided_by"]) for i, v in sorted(st["avc"][a].items()))))


def cmd_set(args):
    if len(args) < 2:
        sys.exit('usage: set <ID> <category[:a+b]> [status] ["note"]')
    st = get_state()
    oid, cat = args[0], args[1]
    between = []
    if ":" in cat:
        cat, b = cat.split(":", 1)
        between = b.split("+")
    cat = "unresolved_cause" if cat == "unresolved" else cat
    if cat not in CATS or any(b not in CATS[:5] for b in between):
        sys.exit("category must be one of: " + ", ".join(CATS))
    if cat == "unresolved_cause" and len(between) < 2:
        sys.exit("unresolved needs the candidates, e.g. unresolved:rubric_interpretation+historical_subjectivity")
    status = args[2] if len(args) > 2 else ("Assumed" if cat == "unresolved_cause" else "Inferred")
    if status not in STATUSES:
        sys.exit("status must be one of: " + ", ".join(STATUSES))
    for cls in ("misses", "false_positives", "deltas"):
        if oid in st[cls]:
            st[cls][oid].update({"category": cat, "between": between, "status": status,
                                 "note": " ".join(args[3:]), "decided_by": "operator"})
            save(STATE, st)
            print("%s -> %s %s" % (oid, cat, status))
            return
    sys.exit("unknown id %s (see: status)" % oid)


def cmd_answer(cls, args):
    st = get_state()
    if cls == "contested":
        if len(args) != 2 or args[1] not in ("yes", "no", "unclear") or args[0] not in st["contested"]:
            sys.exit("usage: cs <ESR strength id> <yes|no|unclear>")
        st["contested"][args[0]].update({"answer": args[1], "decided_by": "operator"})
    else:
        if len(args) != 3 or args[2] not in ("yes", "no", "unclear") or args[0] not in st["avc"] or args[1] not in st["avc"][args[0]]:
            sys.exit("usage: avc <AVC-01|AVC-02> <sample 0-4> <yes|no|unclear>")
        st["avc"][args[0]][args[1]].update({"answer": args[2], "decided_by": "operator"})
    save(STATE, st)
    print("recorded")


def cmd_accept_hints():
    """Take every remaining rule hint as the answer, still marked as decided by rule."""
    st = get_state()
    n = 0
    for v in list(st["contested"].values()) + [x for a in st["avc"].values() for x in a.values()]:
        if v["decided_by"] == "rule":
            v["answer"] = v["hint_by_rule"]
            n += 1
    save(STATE, st)
    print("hints taken as answers, marked by rule: %d" % n)


def cmd_finalize():
    st = get_state()
    cnt = {}

    def bump(k):
        cnt[k] = cnt.get(k, 0) + 1
    for cls in ("misses", "false_positives", "deltas"):
        for v in st[cls].values():
            bump("%s.category.%s" % (cls, v["category"]))
            bump("%s.status.%s" % (cls, v["status"]))
            bump("%s.decided_by.%s" % (cls, v["decided_by"]))
    for v in st["contested"].values():
        bump("contested.answer.%s" % v["answer"])
        bump("contested.decided_by.%s" % v["decided_by"])
    for a in ("AVC-01", "AVC-02"):
        for v in st["avc"][a].values():
            bump("%s.answer.%s" % (a, v["answer"]))
            bump("%s.decided_by.%s" % (a, v["decided_by"]))
    comp = load(os.path.join(R, st["bindings"]["comparison"]))
    summ = comp.get("summary", {})
    rec = {"record_type": "v14_private_diagnosis", "schema_version": "1.0", "advisory": True, "blocking": False,
           "written_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "bindings": st["bindings"], "categories": CATS, "counts": cnt,
           "comparison_by_disposition": summ.get("by_disposition"),
           "misses": st["misses"], "false_positives": st["false_positives"], "deltas": st["deltas"],
           "contested_strengths": st["contested"], "assessor_validation_cases": st["avc"]}
    save(RECORD, rec)
    print("CHECK=v14-diagnosis")
    for k in sorted(cnt):
        print("%s=%d" % (k, cnt[k]))
    bd = summ.get("by_disposition")
    if isinstance(bd, dict):
        for k in sorted(bd):
            if isinstance(bd[k], (int, float)):
                print("comparison.by_disposition.%s=%s" % (k, bd[k]))
    print("comparison_sha256=%s" % st["bindings"]["comparison_sha256"])
    print("record=%s size=%d sha256=%s" % (os.path.relpath(RECORD, R), os.path.getsize(RECORD), sha(RECORD)))


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit("commands: init [--force] | status | set | cs | avc | hints | finalize")
    c, rest = a[0], a[1:]
    if c == "init":
        cmd_init("--force" in rest)
    elif c == "status":
        cmd_status()
    elif c == "set":
        cmd_set(rest)
    elif c == "cs":
        cmd_answer("contested", rest)
    elif c == "avc":
        cmd_answer("avc", rest)
    elif c == "hints":
        cmd_accept_hints()
    elif c == "finalize":
        cmd_finalize()
    else:
        sys.exit("unknown command " + c)


main()
