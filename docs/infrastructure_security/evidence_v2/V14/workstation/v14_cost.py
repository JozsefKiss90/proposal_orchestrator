"""V14 cost from a preflight report: numbers only.

Run on the workstation by the operator, over the private preflight of the
original. Reads token estimates and pack statuses, and prints counts, token
totals and USD. Prints no expectation key, no hash, no path and no text.

usage: py -3.10 v14_cost.py <preflight report> [--n 3] [--criterion-n 5]

Per-call prompt overhead was measured by the V14 rehearsal (REHEARSAL.md):
the largest cell request carried 2,847 characters beyond its pack, the
largest criterion request 4,564 beyond its input. Planned converts characters
at 4 per token (the harness's own estimate); the upper bound at 3, and adds
20% for retries. Output tokens per call are Assumed: 1,000 planned, the
2,048 cap at the upper bound.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

CELL_OVERHEAD_CHARS = 2847
CRITERION_OVERHEAD_CHARS = 4564
INPUT_USD_PER_M = 3.3
OUTPUT_USD_PER_M = 16.5
OUTPUT_PLANNED = 1000
OUTPUT_CAP = 2048
RETRY = 1.2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("preflight", type=Path)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--criterion-n", type=int, default=5)
    a = ap.parse_args()
    d = json.loads(a.preflight.read_text(encoding="utf-8-sig"))

    packs = [p for p in d["packs"] if p.get("status") == "complete"]
    not_built = len(d["packs"]) - len(packs)
    pack_tok = [int(p["token_estimate"]) for p in packs]
    crit_tok = [int(c["token_estimate"]) for c in d["criterion_inputs"]]
    incomplete = sum(1 for c in d["criterion_inputs"] if not c.get("complete"))
    calls = a.n * len(packs) + a.criterion_n * len(crit_tok)

    def total(chars_per_token: float, scale: float) -> int:
        cell = sum(a.n * (t * 4 / chars_per_token + CELL_OVERHEAD_CHARS / chars_per_token)
                   for t in pack_tok)
        crit = sum(a.criterion_n * (t * 4 / chars_per_token + CRITERION_OVERHEAD_CHARS / chars_per_token)
                   for t in crit_tok)
        return math.ceil((cell + crit) * scale)

    in_plan, in_up = total(4, 1.0), total(3, RETRY)
    out_plan, out_up = calls * OUTPUT_PLANNED, math.ceil(calls * OUTPUT_CAP * RETRY)
    usd = lambda t, p: t * p / 1e6  # noqa: E731

    print(f"packs_complete={len(packs)} packs_not_built={not_built} criteria={len(crit_tok)} "
          f"criteria_incomplete={incomplete}")
    print(f"pack_tokens_sum={sum(pack_tok)} pack_tokens_max={max(pack_tok, default=0)} "
          f"criterion_tokens={'/'.join(map(str, crit_tok))}")
    print(f"calls={calls} (n={a.n}, criterion_n={a.criterion_n})")
    print(f"input_tokens planned={in_plan} upper={in_up}")
    print(f"output_tokens planned={out_plan} upper={out_up}")
    print(f"bedrock_usd planned={usd(in_plan, INPUT_USD_PER_M) + usd(out_plan, OUTPUT_USD_PER_M):.2f} "
          f"upper={usd(in_up, INPUT_USD_PER_M) + usd(out_up, OUTPUT_USD_PER_M):.2f}")
    print(f"flags={len(d.get('flags') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
