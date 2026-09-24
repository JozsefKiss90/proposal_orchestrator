"""
Harness module commands — the out-of-band judge runners.

Each module here is a paced, checkpointed, resumable runner over a rate-limited
judge, invoked as ``py -3.10 -m harness.commands.<name>`` from the repo root:

* :mod:`harness.commands.freeze_grounding_baselines` — E4 judge-lane freeze.
* :mod:`harness.commands.faithfulness_calibration` — E1.5 calibration run.
* :mod:`harness.commands.rubric_grading_run` — E5f rubric-grid grading run.

They live inside the harness package (not ``scripts/`` or ``tools/``) so the
one-way ``harness -> runner`` boundary holds for the auxiliary runtime surfaces
too; ``tests/harness/test_boundary.py`` guards that no script or tool imports
the harness.  Advisory artifacts only; never a runtime gate (``harness/HARNESS.md``).
"""

#: The command modules, in the order they were built (E4, E1.5, E5f).
__all__ = ["freeze_grounding_baselines", "faithfulness_calibration", "rubric_grading_run"]
