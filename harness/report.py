"""
Reporting-only output — advisory to a human, never a runtime gate (E1).

The harness's terminal artifact.  It aggregates a metric's :class:`Verdict` /
:class:`MajorityVerdict` findings and the :class:`RoutingDecision`s that governed
them into a single serializable object — and it is, by construction, *advisory*:

* ``advisory`` is always ``True`` and ``blocking`` is always ``False``; a report
  cannot be constructed otherwise.
* There is deliberately **no** method that yields a gate pass/fail the scheduler
  could consume.  A report is data for a human (a merge/release decision), not a
  control signal for a run.

This is the code face of the load-bearing invariant: **no eval metric wires into
the runtime DAG as a fail-closed gate** (strategy §2).  The 138 predicates +
byte-equal CI checks remain the only blocking runtime gates; the harness gates
*decisions about the pipeline*, and even there it advises — it does not
auto-block — until judge reliability is characterized (E1.5).  The prose of that
boundary lives in ``harness/HARNESS.md``; this module makes it structural.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from harness.routing import RoutingDecision
from harness.verdict import MajorityVerdict, Verdict

__all__ = ["Finding", "HarnessReport", "build_report"]

#: A report finding is either a single verdict or a majority verdict.
Finding = Union[Verdict, MajorityVerdict]


@dataclass(frozen=True)
class HarnessReport:
    """An advisory, reporting-only aggregate of one metric's findings.

    Attributes
    ----------
    metric:
        The metric that produced the findings (e.g.
        ``"status_aware_faithfulness"``).
    findings:
        The individual and/or majority verdicts, in order.
    routing:
        The routing decisions taken (which properties were judged vs. left to a
        deterministic predicate); optional but recommended for auditability.
    notes:
        Free-form human context (thresholds applied, caveats).
    judge_model, judge_version:
        The pinned judge identity, when a single judge produced the findings.
    advisory:
        Always ``True`` — rejected otherwise.
    blocking:
        Always ``False`` — rejected otherwise.  The harness never blocks a run.
    """

    metric: str
    findings: tuple[Finding, ...] = ()
    routing: tuple[RoutingDecision, ...] = ()
    notes: str = ""
    judge_model: str | None = None
    judge_version: str | None = None
    advisory: bool = True
    blocking: bool = False

    def __post_init__(self) -> None:
        if self.advisory is not True:
            raise ValueError(
                "HarnessReport.advisory must be True — the harness is advisory to "
                "a human, never authoritative over a run (strategy §2)."
            )
        if self.blocking is not False:
            raise ValueError(
                "HarnessReport.blocking must be False — no eval metric may wire "
                "into the runtime DAG as a fail-closed gate (strategy §2)."
            )

    @property
    def summary(self) -> dict[str, int]:
        """Return pass/fail/inconclusive counts over the boolean findings.

        ``inconclusive`` counts score-only findings (``passed is None``).  These
        are informational tallies for a human reader — not a gate verdict.
        """
        passed = failed = inconclusive = 0
        for f in self.findings:
            if f.passed is True:
                passed += 1
            elif f.passed is False:
                failed += 1
            else:
                inconclusive += 1
        return {
            "total": len(self.findings),
            "passed": passed,
            "failed": failed,
            "inconclusive": inconclusive,
        }

    def to_dict(self) -> dict:
        """Return a JSON-serializable view, boundary flags included."""
        return {
            "record_type": "harness_report",
            "metric": self.metric,
            "advisory": self.advisory,
            "blocking": self.blocking,
            "judge_model": self.judge_model,
            "judge_version": self.judge_version,
            "notes": self.notes,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "routing": [r.to_dict() for r in self.routing],
        }


def build_report(
    metric: str,
    findings: "list[Finding] | tuple[Finding, ...]",
    *,
    routing: "list[RoutingDecision] | tuple[RoutingDecision, ...]" = (),
    notes: str = "",
    judge_model: str | None = None,
    judge_version: str | None = None,
) -> HarnessReport:
    """Construct a :class:`HarnessReport` from findings and routing decisions."""
    return HarnessReport(
        metric=metric,
        findings=tuple(findings),
        routing=tuple(routing),
        notes=notes,
        judge_model=judge_model,
        judge_version=judge_version,
    )
