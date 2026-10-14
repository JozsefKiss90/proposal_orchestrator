"""
The frozen blind baseline — one blind report, checked, copied and bound (spec PE-06).

Why this module exists
----------------------
The blind report is advisory and immutable on its own, but nothing marks
*which* report later stages read.  The integrity audit (PE-07) must show that
the snapshot id it ran over is the one the baseline stamped, and the ESR
comparison (PE-08) is built over "the frozen blind report".  Both need a single
durable record that names the report by content hash and carries every binding
the report declares.  That record is the freeze.

What a freeze checks, and refuses without
-----------------------------------------
A report is frozen only when all of the following hold.  Each is one named
check in :func:`run_baseline_checks`; a failing check names itself, and the
freeze writes nothing.

* The report binds to the candidate hash, profile version and assessor pin
  (``load_report`` has already re-bound it to the candidate on disk).
* The evidence came through the dev-graph route: snapshot id, package id and
  policy version are present.  A directory-route report is never leakage-
  checked and cannot be a baseline.
* The evidence preflight is bound: pack-set hash and preflight report present,
  the preflight file readable, and its ``pack_set_hash`` equal to the one the
  report carries.  A preflight that cannot be re-read is a refusal, not a blank.
* The assessor pin names the transport.  ``assessor_transport`` is present and
  the version tag contains it (spec decision 10).
* The report carries the invocation and isolation evidence its transport is
  able to give (:data:`TRANSPORT_ISOLATION_EVIDENCE`), and the working
  directory it names really does lie outside the repository.  A transport that
  runs no assessor child process declares none, and that check is recorded
  *not applicable* rather than passed.
* Scope is complete.
* The cells are exactly the profile's cell grid
  (:func:`~harness.blind_assessment.expected_cells`) — none missing, none
  extra, none twice — every one with an N>=3 panel, as many members as the
  panel declares, scores on the unit interval, and a majority, agreement and
  mean that come back the same when the members are put through
  :func:`~harness.verdict.majority_vote` again.
* The criterion scores are exactly the profile's criteria, each one's median
  and spread recomputing from its own samples, every sample on the
  scorecard's scale, as many samples as the report declares, and that count
  at least the default panel of five (spec decision 11).
* The total is determined, and it recomputes from the criterion scores under
  the scorecard's own weighting (:func:`~harness.criterion_scoring.weighted_total`).

What a freeze does not do
-------------------------
It does not re-run anything, does not change the report, and does not judge
the scores.  Recomputing a median, a spread or the total re-derives the
report's own arithmetic from the report's own draws; it never substitutes a
number of its own.  A figure that does not reproduce is a refusal, not a
correction.  The spread it copies is **within-assessor repeatability** (spec
decision 11) and the record says so in the same words the report does.

The freeze is advisory and never a runtime gate (``harness/HARNESS.md``).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from runner.atomic_write import atomic_write_json
from harness.blind_assessment import (
    BLIND_REPORT_RECORD_TYPE,
    EVIDENCE_SOURCE_DEV_GRAPH,
    SCOPE_COMPLETE,
    BlindAssessmentError,
    _utc_now,
    expected_cells,
    load_report,
)
from harness.criterion_scoring import (
    DEFAULT_CRITERION_SAMPLES,
    NOT_SCORED,
    SCORED,
    CriterionScoringError,
    median_score,
    off_scale_reason,
    score_factor,
    score_spread,
    weighted_points_for,
    weighted_total,
)
from harness.evidence_preflight import file_sha256, load_preflight
from harness.grounding_scope import (
    SCOPE_SOURCE_GROUNDED,
    UNIT_CELL,
    GroundingScope,
    GroundingScopeError,
    count_grounded,
    scope_for,
    scope_from_record,
    scope_lines,
)
from harness.rubrics import ProfileBundle
from harness.verdict import MIN_MAJORITY_SAMPLES, Verdict, majority_vote

__all__ = [
    "BASELINE_CHECKS",
    "BASELINE_FREEZE_RECORD_TYPE",
    "BASELINE_FREEZE_SCHEMA_VERSION",
    "TRANSPORT_ISOLATION_EVIDENCE",
    "BaselineCheckRun",
    "BlindBaselineError",
    "FrozenBaseline",
    "run_baseline_checks",
    "freeze_baseline",
    "load_frozen_baseline",
    "render_freeze",
]

BASELINE_FREEZE_RECORD_TYPE: str = "harness.blind_baseline_freeze"
#: 1.1.0 adds ``checks_not_applicable`` beside ``checks_passed``.
BASELINE_FREEZE_SCHEMA_VERSION: str = "1.2.0"

#: Every named condition, in the order :func:`run_baseline_checks` runs them.
#: The freeze record's ``checks_passed`` is derived as the checks that ran
#: minus the failures, so it cannot claim a check the function did not make.
BASELINE_CHECKS: tuple[str, ...] = (
    "record_type",
    "binding_fields",
    "evidence_source",
    "evidence_bindings",
    "preflight_binding",
    "preflight_rebound",
    "assessor_transport",
    "pin_names_transport",
    "invocation_evidence",
    "scope",
    "grounding_scope",
    "cells_present",
    "cell_identity",
    "cell_spreads",
    "cell_members",
    "criterion_scores_present",
    "criterion_identity",
    "criterion_spreads",
    "criterion_arithmetic",
    "criterion_samples",
    "criterion_total",
    "total_recomputed",
)

#: The isolation declaration the freeze measures rather than reads, and the
#: field it is measured against.
_OUTSIDE_REPOSITORY: str = "working_directory_outside_repository"
_WORKING_DIRECTORY: str = "working_directory"

#: What a baseline requires one transport's ``assessor_invocation`` to declare.
#: The subscription transport runs an assessor child process and says what it
#: could reach (``harness/commands/_subscription_judge.py``).  The Converse
#: transport runs none, but it records from every request it sent that no
#: request carried a tool configuration (``harness/commands/_converse_judge.py``).
#: With no process and no filesystem, that is its whole claim.  The
#: OpenAI-compatible transport declares nothing, and its ``invocation_evidence``
#: check is recorded not applicable rather than passed.  A transport this table
#: does not know is refused: the freeze cannot say what evidence would be
#: appropriate.
TRANSPORT_ISOLATION_EVIDENCE: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "claude-cli": MappingProxyType({
        "tools": "",
        "strict_mcp_config": True,
        _OUTSIDE_REPOSITORY: True,
    }),
    "bedrock-converse": MappingProxyType({
        "tool_config_sent": False,
        "child_process": False,
    }),
    "openai-compatible": MappingProxyType({}),
})

#: How far a recomputed median, spread, mean or total may sit from the
#: recorded one: the distance a float round-trip can move it, and no more.
_ARITHMETIC_TOLERANCE: float = 1e-9

#: File names under the baseline directory: the byte copy of the report and
#: the freeze record, both named by the report's content hash.
_COPY_NAME: str = "blind_baseline_{short}.json"
_FREEZE_NAME: str = "blind_baseline_{short}.freeze.json"
_FREEZE_GLOB: str = "*.freeze.json"
_SHORT_LEN: int = 12

_FREEZE_NOTE: str = (
    "Frozen blind baseline. Advisory to a human, never run-blocking. Later "
    "stages that claim to read the baseline read the report copy named here "
    "and check its sha256 against report_sha256; a stage whose snapshot id "
    "differs from bindings.snapshot_id has re-derived the baseline and must say "
    "so. Spreads are within-assessor repeatability only."
)


class BlindBaselineError(BlindAssessmentError):
    """The report cannot be frozen, or the frozen record is not what it claims."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# The checks
# --------------------------------------------------------------------------- #


def _present(data: Mapping[str, Any], key: str) -> bool:
    value = data.get(key)
    return value is not None and str(value) != ""


def _resolve_preflight(report: Mapping[str, Any], repo_root: Path | str | None) -> Path | None:
    """The preflight file the report names, as given or under *repo_root*."""
    rel = str(report.get("preflight_report") or "")
    if not rel:
        return None
    candidates = [Path(rel)]
    if repo_root is not None:
        candidates.append(Path(repo_root) / rel)
    for p in candidates:
        if p.is_file():
            return p
    return None


@dataclass(frozen=True)
class BaselineCheckRun:
    """What checking a report established: its failures, and what did not apply.

    ``passed`` is derived — a check is listed only because it ran and did not
    fail — so a conditional check the report's transport cannot answer is
    never claimed as a pass.

    ``grounding_scope`` is the scope the checks established for the report
    (ticket V06): the one it declared, or the measurement alone when it
    declared none.  ``None`` only when neither could be derived, and
    ``grounding_scope`` has then failed.
    """

    failures: tuple[tuple[str, str], ...] = ()
    not_applicable: tuple[tuple[str, str], ...] = ()
    grounding_scope: GroundingScope | None = None

    @property
    def ran(self) -> tuple[str, ...]:
        skipped = {name for name, _ in self.not_applicable}
        return tuple(name for name in BASELINE_CHECKS if name not in skipped)

    @property
    def passed(self) -> tuple[str, ...]:
        failed = {name for name, _ in self.failures}
        return tuple(name for name in self.ran if name not in failed)

    @property
    def ok(self) -> bool:
        return not self.failures


class _Checks:
    """The accumulator the checks record into, under the enumerated names.

    One object rather than a pair of callbacks: every check reports a failure
    or a non-applicability the same way, and :meth:`result` is the only way to
    read the outcome.
    """

    def __init__(self) -> None:
        self._failures: list[tuple[str, str]] = []
        self._not_applicable: list[tuple[str, str]] = []

    def fail(self, name: str, reason: str) -> None:
        assert name in BASELINE_CHECKS, name
        self._failures.append((name, reason))

    def skip(self, name: str, reason: str) -> None:
        """Record that *name* could not apply to this report, with the reason."""
        assert name in BASELINE_CHECKS, name
        self._not_applicable.append((name, reason))

    def result(self, grounding_scope: GroundingScope | None = None) -> BaselineCheckRun:
        return BaselineCheckRun(
            tuple(self._failures), tuple(self._not_applicable), grounding_scope
        )


def _identical(value: Any, required: Any) -> bool:
    """Whether *value* equals *required*, with ``True`` not matching ``1``."""
    if isinstance(required, bool):
        return value is required
    return value == required


def _as_number(value: Any) -> float | None:
    """*value* as a float when it is a real number, else ``None``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _reproduces(recorded: Any, recomputed: float) -> bool:
    number = _as_number(recorded)
    return number is not None and math.isclose(
        number, recomputed, rel_tol=0.0, abs_tol=_ARITHMETIC_TOLERANCE
    )


def _identity_parts(present: Counter, expected: Counter, unknown_label: str) -> list[str]:
    """How *present* differs from *expected*: absent, unexpected, repeated."""
    parts: list[str] = []
    missing = sorted(key for key in expected if not present[key])
    unknown = sorted(key for key in present if key not in expected)
    repeated = sorted(key for key, n in present.items() if n > 1)
    if missing:
        parts.append(f"{len(missing)} absent: {missing}")
    if unknown:
        parts.append(f"{len(unknown)} {unknown_label}: {unknown}")
    if repeated:
        parts.append(f"{len(repeated)} carried more than once: {repeated}")
    return parts


def run_baseline_checks(
    report: Mapping[str, Any], bundle: ProfileBundle, *, repo_root: Path | str | None = None
) -> BaselineCheckRun:
    """Check *report* against the baseline conditions under *bundle*.

    *bundle* is the authority for what a complete report holds: its rubric set
    and criterion map give the expected cell grid and criterion set, and its
    scorecard gives the scale and the weighting the recorded scores must
    reproduce.  The checks are pure over the report dict except for one read:
    the preflight file the report names is loaded and its ``pack_set_hash``
    compared with the report's (``preflight_rebound``).  The candidate
    re-binding is ``load_report``'s and is not repeated here.  Every name this
    function can emit is in :data:`BASELINE_CHECKS`.
    """
    checks = _Checks()
    fail = checks.fail

    if report.get("record_type") != BLIND_REPORT_RECORD_TYPE:
        fail("record_type", f"not a {BLIND_REPORT_RECORD_TYPE!r} record")
    for key in ("candidate_hash", "profile_version", "assessor_pin"):
        if not _present(report, key):
            fail("binding_fields", f"{key} is empty")
    if report.get("evidence_source") != EVIDENCE_SOURCE_DEV_GRAPH:
        fail(
            "evidence_source",
            f"evidence_source is {report.get('evidence_source')!r}; a baseline is built "
            "through the dev-graph route, which is the only one the leakage guard checks",
        )
    for key in ("snapshot_id", "package_id", "policy_version"):
        if not _present(report, key):
            fail("evidence_bindings", f"{key} is empty")
    for key in ("preflight_pack_set_hash", "preflight_report"):
        if not _present(report, key):
            fail("preflight_binding", f"{key} is empty")
    if _present(report, "preflight_report"):
        preflight_path = _resolve_preflight(report, repo_root)
        if preflight_path is None:
            fail(
                "preflight_rebound",
                f"the preflight report {report.get('preflight_report')!r} cannot be read; "
                "a baseline whose preflight is gone cannot be re-bound",
            )
        else:
            try:
                recorded = str(load_preflight(preflight_path).get("pack_set_hash") or "")
            except BlindAssessmentError as exc:
                fail("preflight_rebound", f"the preflight report is not loadable: {exc}")
            else:
                if recorded != str(report.get("preflight_pack_set_hash") or ""):
                    fail(
                        "preflight_rebound",
                        f"the preflight file carries pack_set_hash {recorded!r}, the report "
                        f"{report.get('preflight_pack_set_hash')!r}",
                    )

    transport = str(report.get("assessor_transport") or "")
    version = str(report.get("assessor_version") or "")
    if not transport:
        fail("assessor_transport", "assessor_transport is empty; the report does not say what it spoke")
    elif transport not in version:
        fail(
            "pin_names_transport",
            f"assessor_version {version!r} does not name the transport {transport!r} "
            "(spec decision 10)",
        )

    _check_invocation_evidence(report, repo_root, checks)

    if report.get("scope") != SCOPE_COMPLETE:
        fail("scope", f"scope is {report.get('scope')!r}; a partial candidate is not a baseline")

    grounding = _check_grounding_scope(report, checks)

    cells = report.get("cells")
    if not isinstance(cells, list) or not cells:
        fail("cells_present", "the report carries no cells")
    else:
        _check_cell_identity(cells, bundle, checks)
        for i, cell in enumerate(cells):
            verdict = (cell.get("coverage") or {}).get("verdict") if isinstance(cell, Mapping) else None
            if not isinstance(verdict, Mapping):
                fail("cell_spreads", f"cells[{i}] carries no verdict")
                continue
            n = verdict.get("n")
            if not isinstance(n, int) or n < MIN_MAJORITY_SAMPLES:
                fail("cell_spreads", f"cells[{i}] panel n={n!r}, below {MIN_MAJORITY_SAMPLES}")
            if verdict.get("agreement") is None:
                fail("cell_spreads", f"cells[{i}] carries no agreement value")
            _check_cell_panel(i, cell, verdict, checks)

    scoring = report.get("criterion_scoring")
    if not isinstance(scoring, Mapping):
        fail("criterion_scores_present", "the report carries no criterion_scoring stage")
    else:
        scores = scoring.get("scores")
        if not isinstance(scores, list) or not scores:
            fail("criterion_scores_present", "criterion_scoring carries no scores")
        else:
            _check_criterion_identity(scores, bundle, checks)
            for i, score in enumerate(scores):
                if not isinstance(score, Mapping):
                    fail("criterion_spreads", f"scores[{i}] is not an object")
                    continue
                cid = score.get("criterion_id", f"#{i}")
                if score.get("score") is None:
                    fail("criterion_spreads", f"criterion {cid} is not scored")
                if score.get("spread") is None:
                    fail("criterion_spreads", f"criterion {cid} carries no spread")
                _check_criterion_arithmetic(score, scoring, bundle, checks)
        if scoring.get("unscored_criteria"):
            fail(
                "criterion_scores_present",
                f"unscored criteria: {', '.join(map(str, scoring['unscored_criteria']))}",
            )
        samples = scoring.get("samples_per_criterion")
        if not isinstance(samples, int) or samples < DEFAULT_CRITERION_SAMPLES:
            fail(
                "criterion_samples",
                f"samples_per_criterion is {samples!r}, below the baseline panel of "
                f"{DEFAULT_CRITERION_SAMPLES} (spec decision 11)",
            )
        if scoring.get("total") is None:
            fail("criterion_total", "the total is undetermined")
        _check_total(scoring, bundle, checks)
    return checks.result(grounding)


def _check_grounding_scope(
    report: Mapping[str, Any], checks: _Checks
) -> GroundingScope | None:
    """The scope the baseline binds, so no later stage can overstate it.

    The freeze is where "this run was source-grounded" would be read from, so
    the declaration has to be in the record and has to survive comparison with
    the cells.  Three refusals and one non-applicability:

    * A declared scope the cells contradict — a recorded measurement its own
      grounding values do not give, or a ``source_grounded`` declaration over a
      run that did not assess every cell — fails.
    * A ``source_grounded`` declaration fails while the imported-claim route is
      unimplemented, by the same flag the command refuses it under (X01).
    * A report that declares nothing and whose cells are *not* unanimously
      unassessable fails: there is a grounding result, and a baseline that
      carries one must say which scope produced it.
    * A report that declares nothing and whose cells are unanimously
      unassessable records *not applicable*.  Reports frozen before the
      declaration existed are this case, and the measurement derivation can
      only ever produce the conservative value, so the record states
      unassessable and claims nothing.
    """
    cells = report.get("cells")
    try:
        with_claims, total = count_grounded(cells if isinstance(cells, list) else [])
        recorded = scope_from_record(report)
    except GroundingScopeError as exc:
        checks.fail("grounding_scope", str(exc))
        return None
    declared = recorded.declared if recorded is not None else None
    include_claims = report.get("include_claims")
    if not isinstance(include_claims, bool):
        checks.fail(
            "grounding_scope",
            f"the report records include_claims={include_claims!r}; the grounding scope "
            "cannot be checked against a report that does not say whether the ledger was offered",
        )
        return None
    counted = {
        "include_claims": include_claims,
        "with_claims": with_claims,
        "total": total,
        "unit": UNIT_CELL,
    }
    if declared is None:
        scope = scope_for(None, **counted)
        if total == 0:
            checks.fail(
                "grounding_scope",
                "the report declares no grounding scope and carries no cell to measure one from",
            )
        elif scope.assessable:
            checks.fail(
                "grounding_scope",
                f"the report declares no grounding scope and {scope.reason}; a baseline "
                "that carries a grounding result must declare which scope produced it",
            )
        else:
            checks.skip(
                "grounding_scope",
                f"the report declares no grounding scope, and {scope.reason}; the freeze "
                "records the measurement instead, which can only read "
                f"{scope.measured!r} and never {SCOPE_SOURCE_GROUNDED!r}",
            )
        return scope
    try:
        scope = scope_for(declared, **counted)
    except GroundingScopeError as exc:
        checks.fail("grounding_scope", str(exc))
        return recorded
    # A declared scope can only have come from a block, so recorded is set.
    then_block, now_block = recorded.to_dict(), scope.to_dict()
    differ = [
        f"{key}: report {then_block.get(key)!r}, cells {now_block[key]!r}"
        for key in sorted(now_block)
        if then_block.get(key) != now_block[key]
    ]
    if differ:
        checks.fail(
            "grounding_scope",
            "the recorded grounding scope does not describe the report's own cells; "
            + "; ".join(differ),
        )
    return scope


def _check_invocation_evidence(
    report: Mapping[str, Any], repo_root: Path | str | None, checks: _Checks
) -> None:
    """The transport's own account of what the assessor could reach.

    A baseline is the one report later stages read as blind, so the claim has
    to be in the record rather than only in a test.  What is appropriate
    depends on the transport: :data:`TRANSPORT_ISOLATION_EVIDENCE` says which
    declarations each one owes.

    One of those declarations is measurable rather than merely readable.  A
    transport claiming its working directory lay outside the repository names
    that directory too, and the path either lies under *repo_root* or it does
    not — so the claim is checked against the path, not accepted from the
    report.  Where the caller gave no repository root there is nothing to
    measure against, and the declaration stands alone; the freeze command
    always gives one.
    """
    transport = str(report.get("assessor_transport") or "")
    if not transport:
        checks.skip(
            "invocation_evidence", "the report names no transport (see assessor_transport)"
        )
        return
    required = TRANSPORT_ISOLATION_EVIDENCE.get(transport)
    if required is None:
        checks.fail(
            "invocation_evidence",
            f"transport {transport!r} is not one this freeze knows the isolation evidence "
            f"for (known: {sorted(TRANSPORT_ISOLATION_EVIDENCE)}); a baseline cannot say "
            "what the assessor could reach",
        )
        return
    if not required:
        checks.skip(
            "invocation_evidence",
            f"the {transport} transport runs no assessor child process and declares no "
            "isolation of its own",
        )
        return
    record = report.get("assessor_invocation")
    if not isinstance(record, Mapping) or not record:
        checks.fail(
            "invocation_evidence",
            f"assessor_invocation is {record!r}; the {transport} transport records what its "
            "child process could reach, and a baseline carries that record",
        )
        return
    for key, value in required.items():
        if key not in record:
            checks.fail("invocation_evidence", f"assessor_invocation declares no {key!r}")
        elif not _identical(record[key], value):
            checks.fail(
                "invocation_evidence",
                f"assessor_invocation says {key}={record[key]!r}; a baseline requires {value!r}",
            )
    if _OUTSIDE_REPOSITORY in required:
        _check_working_directory(record, repo_root, checks)



def _check_working_directory(
    record: Mapping[str, Any], repo_root: Path | str | None, checks: _Checks
) -> None:
    """Measure the declared working directory against the repository root."""
    declared = str(record.get(_WORKING_DIRECTORY) or "")
    if not declared:
        checks.fail(
            "invocation_evidence",
            f"assessor_invocation declares {_OUTSIDE_REPOSITORY} and names no "
            f"{_WORKING_DIRECTORY}; the claim cannot be measured",
        )
        return
    if repo_root is None:
        return  # nothing to measure against; the declaration stands alone
    try:
        inside = Path(declared).resolve().is_relative_to(Path(repo_root).resolve())
    except (OSError, ValueError) as exc:  # pragma: no cover - platform-dependent
        checks.fail(
            "invocation_evidence",
            f"the declared {_WORKING_DIRECTORY} {declared!r} cannot be compared with the "
            f"repository root: {exc}",
        )
        return
    if inside:
        checks.fail(
            "invocation_evidence",
            f"assessor_invocation declares {_OUTSIDE_REPOSITORY}=True, but its "
            f"{_WORKING_DIRECTORY} {declared!r} lies under the repository root "
            f"{Path(repo_root).as_posix()}",
        )


def _cell_identity(cell: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(cell.get("criterion_id") or ""),
        str(cell.get("expectation_key") or ""),
        str(cell.get("section_id") or ""),
    )


def _check_cell_identity(cells: list[Any], bundle: ProfileBundle, checks: _Checks) -> None:
    """The cells are the profile's grid: none missing, none extra, none twice.

    The per-cell checks below run over the entries that are present, so a
    report with nine of its ten cells deleted leaves them nothing to refuse.
    This is the check that notices the absence.
    """
    expected = Counter(expected_cells(bundle))
    present = Counter(
        _cell_identity(cell) for cell in cells if isinstance(cell, Mapping)
    )
    malformed = sum(1 for cell in cells if not isinstance(cell, Mapping))
    if malformed:
        checks.fail("cell_identity", f"{malformed} of {len(cells)} cells is not an object")
    if present == expected:
        return
    parts = _identity_parts(present, expected, "not in the profile's grid")
    checks.fail(
        "cell_identity",
        f"the report carries {sum(present.values())} entries for the profile's "
        f"{sum(expected.values())} cells; " + "; ".join(parts),
    )


def _check_cell_panel(
    index: int, cell: Mapping[str, Any], verdict: Mapping[str, Any], checks: _Checks
) -> None:
    """The panel's members, their range, and the three values they determine.

    ``n``, ``agreement``, ``passed`` and ``score`` are a majority vote over
    the members the verdict carries, so the check rebuilds those members and
    puts them back through :func:`~harness.verdict.majority_vote` — the same
    function that produced the recorded values.  A panel that will not
    reconstruct (too few members, or members about different properties) is
    refused with the vote's own reason.  That is what makes a declared panel
    something other than a declaration.
    """
    label = f"cells[{index}] {'/'.join(_cell_identity(cell))}"
    members = verdict.get("members")
    if not isinstance(members, list) or not members:
        checks.fail("cell_members", f"{label} carries no panel members")
        return
    declared_n = verdict.get("n")
    if isinstance(declared_n, int) and len(members) != declared_n:
        checks.fail(
            "cell_members",
            f"{label} declares a panel of {declared_n} and carries {len(members)} member(s)",
        )
    panel: list[Verdict] = []
    for j, member in enumerate(members):
        rebuilt = _rebuild_member(member)
        if isinstance(rebuilt, str):
            checks.fail("cell_members", f"{label} member {j} {rebuilt}")
            continue
        panel.append(rebuilt)
    # Re-vote only over a panel that read cleanly: a member already refused
    # above would otherwise be reported twice, the second time as an aggregate
    # no reader should act on.
    if len(panel) != len(members):
        return
    try:
        recomputed = majority_vote(tuple(panel))
    except ValueError as exc:
        checks.fail("cell_members", f"{label} panel will not re-vote: {exc}")
        return
    for field, recorded in (
        ("score", verdict.get("score")),
        ("agreement", verdict.get("agreement")),
    ):
        value = getattr(recomputed, field)
        if value is not None and not _reproduces(recorded, value):
            checks.fail(
                "cell_members",
                f"{label} records {field} {recorded!r}; its {recomputed.n} members give {value}",
            )
    if verdict.get("passed") is not recomputed.passed:
        checks.fail(
            "cell_members",
            f"{label} records passed={verdict.get('passed')!r}; the majority of its "
            f"{recomputed.n} members gives {recomputed.passed!r} (a tie resolves to False)",
        )
    if cell.get("score") is not None and recomputed.score is not None:
        if not _reproduces(cell.get("score"), recomputed.score):
            checks.fail(
                "cell_members",
                f"{label} records score {cell.get('score')!r} beside a panel score of "
                f"{recomputed.score}",
            )


def _rebuild_member(member: Any) -> Verdict | str:
    """One recorded panel member as a :class:`~harness.verdict.Verdict`.

    Returns the reason it cannot be rebuilt instead, so the panel is refused
    by name rather than by a raised constructor error.  A baseline's members
    each carry a vote and a score on the unit interval; without both, the
    majority rule has nothing to re-derive.
    """
    if not isinstance(member, Mapping):
        return "is not an object"
    if not isinstance(member.get("passed"), bool):
        return (
            f"declares passed={member.get('passed')!r}; a baseline's panel members each "
            "cast a vote"
        )
    value = member.get("score")
    if value is None:
        return "declares no score"
    number = _as_number(value)
    if number is None:
        return f"scores {value!r}, which is not a number"
    if not 0.0 <= number <= 1.0:
        return f"scores {number}, outside the unit interval"
    return Verdict(
        metric=str(member.get("metric") or ""),
        property_key=str(member.get("property_key") or ""),
        passed=bool(member["passed"]),
        score=number,
        rationale=str(member.get("rationale") or ""),
    )


def _check_criterion_identity(
    scores: list[Any], bundle: ProfileBundle, checks: _Checks
) -> None:
    """The criterion scores are the profile's criteria, each exactly once."""
    expected = Counter(bundle.profile.criterion_ids)
    present = Counter(
        str(score.get("criterion_id") or "") for score in scores if isinstance(score, Mapping)
    )
    if present == expected:
        return
    parts = _identity_parts(
        present, expected, f"not a criterion of profile {bundle.profile_id!r}"
    )
    checks.fail(
        "criterion_identity",
        f"the report carries {sum(present.values())} score(s) for the profile's "
        f"{sum(expected.values())} criteria; " + "; ".join(parts),
    )


def _check_criterion_arithmetic(
    score: Mapping[str, Any],
    scoring: Mapping[str, Any],
    bundle: ProfileBundle,
    checks: _Checks,
) -> None:
    """One criterion's median, spread, sample count and weighting, re-derived.

    Only a scored criterion is checked: a criterion the report says was not
    scored carries no samples by design, and ``criterion_scores_present``
    already refuses a baseline with one.
    """
    cid = str(score.get("criterion_id") or "")
    label = f"criterion {cid or '(unnamed)'}"
    if score.get("status") == NOT_SCORED:
        return
    if score.get("status") != SCORED:
        checks.fail("criterion_arithmetic", f"{label} carries status {score.get('status')!r}")
        return
    samples = score.get("samples")
    if not isinstance(samples, list) or not samples:
        checks.fail("criterion_arithmetic", f"{label} is scored and carries no samples")
        return
    declared = scoring.get("samples_per_criterion")
    if isinstance(declared, int) and len(samples) != declared:
        checks.fail(
            "criterion_arithmetic",
            f"{label} carries {len(samples)} sample(s); the report declares {declared} "
            "per criterion",
        )
    values: list[float] = []
    for j, sample in enumerate(samples):
        value = _as_number(sample.get("score")) if isinstance(sample, Mapping) else None
        if value is None:
            checks.fail("criterion_arithmetic", f"{label} sample {j} carries no numeric score")
            continue
        off_scale = off_scale_reason(value, bundle.scoring)
        if off_scale is not None:
            checks.fail("criterion_arithmetic", f"{label} sample {j} scores {off_scale}")
        else:
            values.append(value)
    if len(values) != len(samples):
        return
    if not _reproduces(score.get("score"), median_score(values)):
        checks.fail(
            "criterion_arithmetic",
            f"{label} records {score.get('score')!r}; the median of its {len(values)} "
            f"sample(s) is {median_score(values)}",
        )
    if not _reproduces(score.get("spread"), score_spread(values)):
        checks.fail(
            "criterion_arithmetic",
            f"{label} records spread {score.get('spread')!r}; its samples span "
            f"{score_spread(values)}",
        )
    if cid not in bundle.scoring.weights:
        checks.fail(
            "criterion_arithmetic",
            f"{label} is not a criterion the scorecard weights, so its weighting cannot "
            f"be re-derived (weighted: {sorted(bundle.scoring.weights)})",
        )
        return
    factor = score_factor(bundle.scoring, cid)
    if not _reproduces(score.get("weight"), float(bundle.scoring.weights[cid])):
        checks.fail(
            "criterion_arithmetic",
            f"{label} records weight {score.get('weight')!r}; the scorecard weights it "
            f"{bundle.scoring.weights[cid]}",
        )
    if not _reproduces(score.get("factor"), factor):
        checks.fail(
            "criterion_arithmetic",
            f"{label} records factor {score.get('factor')!r}; the scorecard gives {factor}",
        )
    recorded_score = _as_number(score.get("score"))
    if recorded_score is not None and not _reproduces(
        score.get("weighted_points"), weighted_points_for(recorded_score, factor)
    ):
        checks.fail(
            "criterion_arithmetic",
            f"{label} records {score.get('weighted_points')!r} weighted point(s); "
            f"{recorded_score} x {factor} is {weighted_points_for(recorded_score, factor)}",
        )


def _check_total(
    scoring: Mapping[str, Any], bundle: ProfileBundle, checks: _Checks
) -> None:
    """The aggregate, recomputed from the criterion scores the report carries.

    ``criterion_total`` only asks whether a total is there.  This asks whether
    it is the total of these scores under this scorecard — the check a report
    whose total was replaced by any other number must fail.
    """
    scores = scoring.get("scores")
    if not isinstance(scores, list):
        return
    recorded_total = scoring.get("total")
    present: dict[str, float] = {}
    for score in scores:
        if not isinstance(score, Mapping) or score.get("status") != SCORED:
            continue
        value = _as_number(score.get("score"))
        if value is not None:
            present[str(score.get("criterion_id") or "")] = value
    try:
        recomputed = weighted_total(present, bundle.scoring)
    except CriterionScoringError as exc:
        checks.fail("total_recomputed", f"the total cannot be recomputed: {exc}")
        return
    if recorded_total is None:
        return  # criterion_total already names the undetermined total
    if not _reproduces(recorded_total, recomputed):
        checks.fail(
            "total_recomputed",
            f"the report records a total of {recorded_total!r}; "
            f"{scoring.get('formula') or 'the scorecard weighting'} over its criterion "
            f"scores gives {recomputed}",
        )
    for key, expected in (
        ("overall_max", bundle.scoring.overall_max),
        ("overall_threshold", bundle.scoring.overall_threshold),
    ):
        if not _reproduces(scoring.get(key), float(expected)):
            checks.fail(
                "total_recomputed",
                f"the report records {key}={scoring.get(key)!r}; the scorecard declares {expected}",
            )
    met = scoring.get("overall_threshold_met")
    if met is not (recomputed >= bundle.scoring.overall_threshold):
        checks.fail(
            "total_recomputed",
            f"the report records overall_threshold_met={met!r} for a total of {recomputed} "
            f"against a threshold of {bundle.scoring.overall_threshold}",
        )


# --------------------------------------------------------------------------- #
# The record
# --------------------------------------------------------------------------- #


def _cell_summary(cell: Mapping[str, Any]) -> dict[str, Any]:
    verdict = (cell.get("coverage") or {}).get("verdict") or {}
    members = verdict.get("members") or []
    scores: list[float] = [
        float(m["score"]) for m in members
        if isinstance(m, Mapping) and isinstance(m.get("score"), (int, float))
    ]
    return {
        "criterion_id": cell.get("criterion_id"),
        "expectation_key": cell.get("expectation_key"),
        "section_id": cell.get("section_id"),
        "addressal": cell.get("addressal"),
        "grounding": cell.get("grounding"),
        "clean_pass": cell.get("clean_pass"),
        "score": cell.get("score"),
        "n": verdict.get("n"),
        "agreement": verdict.get("agreement"),
        "score_spread": (round(max(scores) - min(scores), 4) if len(scores) >= 2 else None),
    }


def _criterion_summary(score: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "criterion_id": score.get("criterion_id"),
        "score": score.get("score"),
        "spread": score.get("spread"),
        "threshold": score.get("threshold"),
        "threshold_met": score.get("threshold_met"),
        "weighted_points": score.get("weighted_points"),
        "input_hash": score.get("input_hash"),
        "shortcomings": score.get("shortcomings"),
    }


_BINDING_KEYS: tuple[str, ...] = (
    "candidate_hash",
    "candidate_path",
    "profile_id",
    "profile_version",
    "assessor_model",
    "assessor_version",
    "assessor_pin",
    "assessor_transport",
    "snapshot_id",
    "package_id",
    "policy_version",
    "evidence_view",
    "evidence_source",
    "preflight_pack_set_hash",
    "preflight_report",
    "rubric_set_id",
    "rubric_set_version",
    "rubric_set_fingerprint",
    "scorecard_id",
    "scorecard_version",
    "include_claims",
    "intake_id",
    "esr_availability",
    "assessed_at",
    "assessor_invocation",
)


@dataclass(frozen=True)
class FrozenBaseline:
    """The freeze record and the paths it was written to."""

    record: dict[str, Any]
    freeze_path: Path
    copy_path: Path


def _build_record(
    report: Mapping[str, Any],
    *,
    report_path: str,
    report_sha256: str,
    copy_name: str,
    preflight_sha256: str,
    frozen_at: str,
    checks: BaselineCheckRun,
) -> dict[str, Any]:
    scoring = report.get("criterion_scoring") or {}
    return {
        "record_type": BASELINE_FREEZE_RECORD_TYPE,
        "schema_version": BASELINE_FREEZE_SCHEMA_VERSION,
        "advisory": True,
        "blocking": False,
        "frozen_at": frozen_at,
        "report_path": report_path,
        "report_sha256": report_sha256,
        "report_copy": copy_name,
        "bindings": {key: report.get(key) for key in _BINDING_KEYS},
        "preflight_report_sha256": preflight_sha256,
        # Derived, not declared: a check is listed only because it ran and did
        # not fail.  An empty failure list is the only way to reach this point,
        # and a check the report's transport could not answer is listed as not
        # applicable rather than passed.
        "checks_passed": list(checks.passed),
        # The scope the checks established, bound here rather than under
        # ``bindings``: a later stage reads it to learn what this baseline
        # assessed, and a run that declared none still records what it measured.
        "grounding_scope": (
            checks.grounding_scope.to_dict() if checks.grounding_scope is not None else None
        ),
        "checks_not_applicable": [
            {"check": name, "reason": reason} for name, reason in checks.not_applicable
        ],
        "cells": [_cell_summary(c) for c in report.get("cells", [])],
        "criterion_scores": [_criterion_summary(s) for s in scoring.get("scores", [])],
        "criterion_total": {
            "formula": scoring.get("formula"),
            "total": scoring.get("total"),
            "overall_max": scoring.get("overall_max"),
            "overall_threshold": scoring.get("overall_threshold"),
            "overall_threshold_met": scoring.get("overall_threshold_met"),
            "samples_per_criterion": scoring.get("samples_per_criterion"),
        },
        "spread_label": scoring.get("spread_label"),
        "summary": report.get("summary"),
        "notes": _FREEZE_NOTE,
    }


def freeze_baseline(
    report_path: Path | str,
    candidate_dir: Path | str,
    bundle: ProfileBundle,
    *,
    baseline_dir: Path | str,
    repo_root: Path | str | None = None,
    clock: Callable[[], str] | None = None,
) -> FrozenBaseline:
    """Check *report_path*, copy it under *baseline_dir* and write the freeze record.

    *bundle* is the loaded profile the report must have been produced under:
    it supplies the version the report is re-bound to, the cell grid and
    criterion set the report must carry in full, and the scale and weighting
    its scores must reproduce.  A profile alone cannot answer those, which is
    why the bundle is the argument.

    Raises :class:`BlindBaselineError` when any check fails or when
    *baseline_dir* already holds a freeze: a frozen baseline is not replaced,
    a second baseline goes in another directory.  Nothing is written on
    refusal.
    """
    path = Path(report_path)
    data = load_report(path, candidate_dir, bundle.profile, profile_version=bundle.version)
    checks = run_baseline_checks(data, bundle, repo_root=repo_root)
    if not checks.ok:
        lines = "; ".join(f"{name}: {reason}" for name, reason in checks.failures)
        raise BlindBaselineError(f"report {path} cannot be frozen as a baseline: {lines}")

    target = Path(baseline_dir)
    existing = sorted(target.glob(_FREEZE_GLOB)) if target.is_dir() else []
    if existing:
        raise BlindBaselineError(
            f"{target} already holds a frozen baseline ({existing[0].name}); a frozen "
            "baseline is never replaced. Freeze a second baseline into another directory."
        )

    digest = _sha256_bytes(path.read_bytes())
    short = digest[:_SHORT_LEN]
    copy_path = target / _COPY_NAME.format(short=short)
    freeze_path = target / _FREEZE_NAME.format(short=short)
    if copy_path.exists() or freeze_path.exists():
        raise BlindBaselineError(f"{copy_path} or {freeze_path} already exists; nothing overwritten.")

    # check_baseline_report has already established the file exists and re-binds.
    preflight_path = _resolve_preflight(data, repo_root)
    assert preflight_path is not None
    record = _build_record(
        data,
        report_path=_portable(path, repo_root),
        report_sha256=digest,
        copy_name=copy_path.name,
        preflight_sha256=file_sha256(preflight_path),
        frozen_at=(clock or _utc_now)(),
        checks=checks,
    )
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, copy_path)
    atomic_write_json(record, freeze_path)
    return FrozenBaseline(record=record, freeze_path=freeze_path, copy_path=copy_path)


def _portable(path: Path, repo_root: Path | str | None) -> str:
    """*path* relative to *repo_root* when it lies under it, else as given."""
    if repo_root is not None:
        try:
            return path.resolve().relative_to(Path(repo_root).resolve()).as_posix()
        except ValueError:
            pass
    return path.as_posix()


def load_frozen_baseline(baseline_dir: Path | str) -> FrozenBaseline:
    """Load the one freeze under *baseline_dir* and check the copy's hash.

    Later stages read the baseline through this so a copy edited after the
    freeze is refused rather than read.
    """
    target = Path(baseline_dir)
    freezes = sorted(target.glob(_FREEZE_GLOB)) if target.is_dir() else []
    if not freezes:
        raise BlindBaselineError(f"{target} holds no frozen baseline.")
    if len(freezes) > 1:
        raise BlindBaselineError(
            f"{target} holds {len(freezes)} freeze records; a baseline directory holds one."
        )
    freeze_path = freezes[0]
    try:
        record = json.loads(freeze_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise BlindBaselineError(f"{freeze_path} is not valid JSON: {exc}") from exc
    if not isinstance(record, Mapping) or record.get("record_type") != BASELINE_FREEZE_RECORD_TYPE:
        raise BlindBaselineError(f"{freeze_path} is not a {BASELINE_FREEZE_RECORD_TYPE!r} record.")
    if record.get("advisory") is not True or record.get("blocking") is not False:
        raise BlindBaselineError(f"{freeze_path} must carry advisory=true and blocking=false.")
    copy_name = str(record.get("report_copy") or "")
    if not re.fullmatch(r"blind_baseline_[0-9a-f]{%d}\.json" % _SHORT_LEN, copy_name):
        raise BlindBaselineError(f"{freeze_path} names an unexpected report copy {copy_name!r}.")
    copy_path = target / copy_name
    if not copy_path.is_file():
        raise BlindBaselineError(f"the frozen report copy {copy_path} is missing.")
    actual = file_sha256(copy_path)
    if actual != record.get("report_sha256"):
        raise BlindBaselineError(
            f"the frozen report copy {copy_path} hashes to {actual}, the freeze says "
            f"{record.get('report_sha256')}; the baseline was edited after it was frozen."
        )
    return FrozenBaseline(record=dict(record), freeze_path=freeze_path, copy_path=copy_path)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _measured_from_freeze(record: Mapping[str, Any]) -> GroundingScope:
    """The grounding a freeze record's own cell summaries give.

    Reached only by a freeze record written before the scope block existed:
    the summaries carry each cell's grounding value and the bindings carry
    ``include_claims``, so the measurement is derivable and the rendered
    screen never goes silent on grounding.
    """
    with_claims, total = count_grounded(record.get("cells") or [])
    return scope_for(
        None,
        include_claims=bool((record.get("bindings") or {}).get("include_claims", True)),
        with_claims=with_claims,
        total=total,
        unit=UNIT_CELL,
    )


def render_freeze(record: Mapping[str, Any]) -> str:
    """One screen of text: what was frozen and what it is bound to."""
    b = record.get("bindings") or {}
    lines = [
        f"FROZEN BLIND BASELINE  {record.get('report_copy')}",
        f"report sha256: {record.get('report_sha256')}",
        f"frozen at:     {record.get('frozen_at')}",
        f"candidate:     {str(b.get('candidate_hash') or '')[:19]}",
        f"profile:       {b.get('profile_id')} [{str(b.get('profile_version') or '')[:19]}]",
        f"assessor:      {b.get('assessor_pin')}  transport={b.get('assessor_transport')}",
        f"snapshot:      {str(b.get('snapshot_id') or '')[:19]}  package={str(b.get('package_id') or '')[:19]}",
        f"preflight:     pack set {str(b.get('preflight_pack_set_hash') or '')[:19]}  {b.get('preflight_report')}",
        f"cells:         {len(record.get('cells') or [])}  "
        f"criterion scores: {len(record.get('criterion_scores') or [])}",
    ]
    total = record.get("criterion_total") or {}
    if total.get("total") is not None:
        lines.append(
            f"total:         {total.get('formula')} = {total.get('total')} / {total.get('overall_max')}"
        )
    for s in record.get("criterion_scores") or []:
        lines.append(
            f"  - {s.get('criterion_id')}: {s.get('score')} (spread {s.get('spread')})"
        )
    lines.extend(scope_lines(record, lambda: _measured_from_freeze(record)))
    lines.append(f"spread label:  {record.get('spread_label')}")
    passed = record.get("checks_passed") or []
    skipped = record.get("checks_not_applicable") or []
    lines.append(f"checks:        {len(passed)} of {len(BASELINE_CHECKS)} passed")
    for row in skipped:
        lines.append(f"  not applicable: {row.get('check')} - {row.get('reason')}")
    return "\n".join(lines)
