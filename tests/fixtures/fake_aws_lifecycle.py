"""A fake AWS CLI for the host-lifecycle script tests (ticket R14).

Each call appends its argv to FAKE_AWS_LOG (one JSON line) and answers from FAKE_AWS_SCENARIO, a JSON
object mapping a key to a list of answers ``{"out": str, "rc": int}``. The key is ``"<service> <op>"``
(``"<service> wait <waiter>"`` for waiters); ``"<key>|<query>"`` answers that query only. The n-th call
of a key takes the n-th answer, and the last answer repeats. A key absent from the scenario answers
``""`` with exit 0.
"""
from __future__ import annotations

import json
import os
import sys


def main(argv: list[str]) -> int:
    args = list(argv)
    if len(args) < 2 or args[0].startswith("--"):
        key = args[0] if args else ""
    elif args[1] == "wait":
        key = f"{args[0]} wait {args[2]}"
    else:
        key = f"{args[0]} {args[1]}"
    query = args[args.index("--query") + 1] if "--query" in args else None
    lookup = f"{key}|{query}" if query is not None else key

    with open(os.environ["FAKE_AWS_SCENARIO"], encoding="utf-8") as handle:
        scenario = json.load(handle)
    if lookup not in scenario:
        lookup = key
    log_path = os.environ["FAKE_AWS_LOG"]
    seen = 0
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as handle:
            seen = sum(1 for line in handle if json.loads(line)["lookup"] == lookup)
    # A file:// argument is read at call time, as the real CLI reads it (the R15 sender deletes it after).
    files = {}
    for arg in args:
        if arg.startswith("file://") and os.path.isfile(arg[7:]):
            with open(arg[7:], "rb") as handle:
                files[arg] = handle.read().decode("utf-8", "replace")
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"argv": args, "lookup": lookup, "files": files}) + "\n")

    answers = scenario.get(lookup) or [{"out": "", "rc": 0}]
    answer = answers[min(seen, len(answers) - 1)]
    stream = sys.stdout if answer.get("rc", 0) == 0 else sys.stderr
    stream.write(answer.get("out", ""))
    if answer.get("out"):
        stream.write("\n")
    return int(answer.get("rc", 0))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
