"""
Harness module commands — the out-of-band judge runners.

Each module here is a paced, checkpointed, resumable runner over a rate-limited
judge, invoked as ``py -3.10 -m harness.commands.<name>`` from the repo root:

* :mod:`harness.commands.freeze_grounding_baselines` — E4 judge-lane freeze.
* :mod:`harness.commands.faithfulness_calibration` — E1.5 calibration run.
* :mod:`harness.commands.rubric_grading_run` — E5f rubric-grid grading run.
* :mod:`harness.commands.blind_assessment` — candidate-bound blind assessment.
* :mod:`harness.commands.deferral_register` — reads an open-deferral register.
* :mod:`harness.commands.authority_matrix` — reads a rule-equivalence matrix.

The last two are readers rather than judge runners: they invoke no judge, write a
Markdown reading of a declaration and exit non-zero on a finding. They are listed
here so ``tests/harness/test_boundary.py`` parametrises over them too.

They live inside the harness package (not ``scripts/`` or ``tools/``) so the
one-way ``harness -> runner`` boundary holds for the auxiliary runtime surfaces
too; ``tests/harness/test_boundary.py`` guards that no script or tool imports
the harness.  Advisory artifacts only; never a runtime gate (``harness/HARNESS.md``).
"""

#: The command modules, in the order they were built (E4, E1.5, E5f, blind lane,
#: then the two declaration readers).
__all__ = [
    "freeze_grounding_baselines",
    "faithfulness_calibration",
    "rubric_grading_run",
    "blind_assessment",
    "deferral_register",
    "authority_matrix",
]
