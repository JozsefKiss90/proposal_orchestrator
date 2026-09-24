"""
Shared bootstrap for the harness module commands.

Two things every command needs and nothing else should re-implement: the repo
root (anchored on this file, so the commands work from any working directory)
and the ``.env.harness`` loader, which must run from ``main()`` — never at
import — so importing a command module does not mutate ``os.environ``.
"""
from __future__ import annotations

from pathlib import Path

from runner.paths import find_repo_root

#: The repository root — anchors ``.env.harness`` discovery and the default
#: gold-set / checkpoint paths of the commands.
REPO_ROOT: Path = find_repo_root(Path(__file__).resolve().parent)


def load_harness_env() -> None:
    """Load a dedicated ``.env.harness`` (if present), overriding the pipeline's
    ``.env`` for judge/transport keys only.

    ``HARNESS_COST_POLICY.md`` intends the judge config to live apart from the
    pipeline's ``.env`` (which points at the Bedrock/Claude drafter transport).
    ``runner.transport.config`` loads ``.env`` at import with ``override=False``
    and reads ``os.environ`` at resolve time; loading ``.env.harness`` here with
    ``override=True`` makes the harness file win, so ``HARNESS_JUDGE_*`` and the
    Groq ``ORCHESTRATOR_TRANSPORT_*`` need never be exported by hand.  Absent
    file or absent python-dotenv: harmless no-op (fall back to real env vars).

    Called from each command's ``main()`` — never at import — so importing a
    command module (tests, other commands) does not mutate the process
    environment and flip the pipeline's transport preset.
    """
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    for name in (".env.harness", ".env.judge"):
        p = REPO_ROOT / name
        if p.is_file():
            load_dotenv(p, override=True)
            return
