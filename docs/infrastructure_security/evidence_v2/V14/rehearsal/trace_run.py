"""Run one ``python -m`` command in the current tree and record every file it opens.

Usage: py -3.10 trace_run.py <trace.json> [--fake-converse] <module> [args...]

The current directory is the tree under test; it is put first on sys.path.
--fake-converse replaces boto3.client with a scripted Converse client, so no
network call is made, and records the size of every request it receives.
Only paths, counts and sizes are written; no prompt text.
"""
from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path

out = Path(sys.argv[1]).resolve()
args = sys.argv[2:]
fake = False
if args and args[0] == "--fake-converse":
    fake = True
    args = args[1:]
module, rest = args[0], args[1:]

tree = Path.cwd().resolve()
sys.path.insert(0, str(tree))
opened: set[str] = set()


def _hook(event: str, a: tuple) -> None:
    if event == "open" and a and isinstance(a[0], (str, bytes, os.PathLike)):
        p = a[0]
        if isinstance(p, bytes):
            p = p.decode(errors="replace")
        opened.add(os.path.abspath(os.fspath(p)))


sizes: list[dict] = []
if fake:
    os.environ.pop("ORCHESTRATOR_TRANSPORT_PRESET", None)
    os.environ.pop("ORCHESTRATOR_PRODUCTION_MODE", None)
    os.environ["ORCHESTRATOR_TRANSPORT_BACKEND"] = "bedrock_converse"
    os.environ["ORCHESTRATOR_TRANSPORT_MODEL"] = "env-default-model"
    os.environ["AWS_REGION"] = "eu-north-1"
    os.environ["HARNESS_JUDGE_MAX_TOKENS"] = "2048"
    import boto3  # noqa: E402

    PASS_JSON = '{"passed": true, "score": 0.9, "rationale": "scripted pass"}'
    CRITERION_JSON = json.dumps({"score": 4.0, "shortcomings": ["one named shortcoming"],
                                 "strengths": ["s"], "rationale": "scripted criterion score"})

    class _Fake:
        def converse(self, **kw):
            system = "\n".join(b.get("text", "") for b in kw.get("system", []))
            user = "".join(b.get("text", "") for m in kw["messages"] for b in m["content"])
            crit = "CRITERION UNDER ASSESSMENT" in system
            sizes.append({"kind": "criterion" if crit else "cell",
                          "chars": len(system) + len(user),
                          "max_tokens": kw.get("inferenceConfig", {}).get("maxTokens")})
            return {"output": {"message": {"role": "assistant",
                                           "content": [{"text": CRITERION_JSON if crit else PASS_JSON}]}},
                    "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15}}

    boto3.client = lambda service, **_k: _Fake()

import harness.commands._common as _c  # noqa: E402
_c.load_harness_env = lambda: None

sys.addaudithook(_hook)
sys.argv = [module] + rest
code = 0
try:
    if module.startswith("inproc:"):
        import importlib
        module = module[len("inproc:"):]
        code = importlib.import_module(module).main(rest) or 0
    else:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
except SystemExit as e:
    code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)

inside = sorted({Path(p).relative_to(tree).as_posix() for p in opened
                 if Path(p).is_file() and Path(p).is_relative_to(tree)
                 and ".pyc" not in p and "__pycache__" not in p})
outside = sorted({p for p in opened if Path(p).is_file() and not Path(p).is_relative_to(tree)
                  and "site-packages" not in p and "Python310" not in p})
out.write_text(json.dumps({"module": module, "exit": code, "tree": str(tree),
                           "opened_in_tree": inside, "opened_outside_tree": outside,
                           "converse_requests": sizes}, indent=1), encoding="utf-8")
print(f"TRACE {module} exit={code} in_tree={len(inside)} outside={len(outside)} calls={len(sizes)}",
      file=sys.stderr)
sys.exit(code)
