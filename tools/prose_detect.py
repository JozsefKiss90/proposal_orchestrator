"""Prose detect pass (pass 1 of docs/style/proposal-prose-profile.md).

Measures human-facing prose against the profile's mechanical rules: sentence
length, em-dash count, clause-vs-list semicolons (reported, not judged),
paragraph length and watch words. Detection only. It never edits anything;
the edit pass is a separate, human-reviewed step (for the condensed Part B-1,
through tools/build_partb1_condensed.py).

Targets:
  py -3.10 tools/prose_detect.py --builder
      measures the condensed Part B-1 content blocks in build_partb1_condensed.py
  py -3.10 tools/prose_detect.py docs/tier5_deliverables/proposal_sections/<file>.json
      measures every string value in the JSON (text fields; keys are ignored)

The profile is an execution aid under CLAUDE.md §10.2. This tool reports; a
human rules on enumeration exceptions and list punctuation. Run-in bold
lead-ins in the builder are labels, not sentences, and are excluded.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ABBREV = ("Dr.", "Prof.", "et al.", "e.g.", "i.e.", "incl.", "cf.", "vs.",
          "No.", "approx.", "Kft.", "MSc.", "BSc.")
WATCH = ["directly", "ensures", "ensure", "explicitly", "specifically",
         "rigorous", "state of the art", "critical", "genuinely", "genuine",
         "deliberately", "precisely", "seamless", "robust", "leverage",
         "delve", "moreover", "furthermore", "streamline", "transformative"]


def split_sentences(text: str) -> list[str]:
    t = text
    for a in ABBREV:
        t = t.replace(a, a.replace(".", "\x00"))
    t = re.sub(r"(\d)\.(\d)", "\\1\x00\\2", t)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(\u201c\d])", t)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


def iter_builder_paragraphs():
    spec = importlib.util.spec_from_file_location(
        "partb1_builder", REPO / "tools" / "build_partb1_condensed.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # module level builds content; no rendering
    section = "front"
    for b in mod.C["blocks"]:
        if b["kind"] == "h" and b["level"] in (1, 2):
            section = b["text"].split(" ")[0]
        elif b["kind"] == "p":
            yield section, b["text"]  # lead-ins are labels, excluded
        elif b["kind"] == "img":
            yield section, b["caption"]


def iter_json_strings(path: Path):
    def walk(node, crumb):
        if isinstance(node, str):
            if len(node.split()) >= 8:  # skip ids, labels, enum values
                yield crumb, node
        elif isinstance(node, dict):
            for k, v in node.items():
                yield from walk(v, f"{crumb}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, f"{crumb}[{i}]")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    yield from walk(data, path.stem)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--builder":
        units = list(iter_builder_paragraphs())
    else:
        units = list(iter_json_strings(REPO / argv[0]))

    rows, semis, watch_hits, emdash, over6 = [], [], Counter(), Counter(), []
    for label, text in units:
        emdash[label] += text.count("\u2014")
        sents = split_sentences(text)
        if len(sents) > 6:
            over6.append((label, len(sents)))
        for s in sents:
            w = len(s.split())
            rows.append((label, w, s))
            if ";" in s:
                semis.append((label, s))
            low = s.lower()
            for word in WATCH:
                watch_hits[word] += len(
                    re.findall(r"\b" + re.escape(word) + r"\b", low))

    if not rows:
        print("no prose found")
        return 1
    n = len(rows)
    words = sum(w for _, w, _ in rows)
    over25 = [r for r in rows if r[1] > 25]
    over35 = [r for r in rows if r[1] > 35]
    print(f"{words} words, {n} sentences, mean {words / n:.1f} w/sentence")
    print(f"over 25: {len(over25)} ({100 * len(over25) / n:.0f}%)   "
          f"over 35: {len(over35)}   longest: {max(w for _, w, _ in rows)}")
    print(f"em-dashes: {sum(emdash.values())}   "
          f"sentences with ';': {len(semis)}   units over 6 sentences: {len(over6)}")
    hits = {k: v for k, v in watch_hits.most_common() if v}
    print(f"watch words: {hits}")
    for label, cnt in over6:
        print(f"  [>6 sentences] {label}: {cnt}")
    print()
    print("=== SENTENCES OVER 35 WORDS (worst first; rule on each: split, or a "
          "declared enumeration exception) ===")
    for label, w, s in sorted(over35, key=lambda r: -r[1]):
        print(f"\n[{label} | {w}w] {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
