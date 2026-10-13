"""Author the 2025 historical pre-evaluation profile from the V09 equivalence matrix.

Ticket V10 of ``plans/msca_dn_historical_validation_tickets.md``. The only
Doctoral Networks profile at the previous revision was written for the 2026
call. Assessing the 2025 original under it would score a historical submission
by a later year's configuration, and nothing in the artifact would say so.

This module writes a second profile. Every element of it names the matrix rows
that establish what the 2025 call's rule was, and every element the matrix
leaves open carries a declared limitation instead. Those two cases are the whole
design: a profile that could not say which of its rules were sourced would be a
copy of the 2026 one wearing a different ``profile_id``.

Three rules the derivation holds to:

* **Nothing is typed that the matrix states.** The criteria, their order, the
  weights, the thresholds, the scale and the structural authority are read out
  of the matrix rows and the records those rows cite. A value this module typed
  would be a value the matrix does not vouch for.
* **A row's verdict decides how its element is written.** An ``equivalent`` or
  ``differs`` row sources an element. An ``unresolved`` row cannot, and the
  element it would have sourced carries a limitation naming the row.
* **The matrix is pinned.** The profile records the matrix path and the sha256
  of its bytes, so a profile read beside a moved matrix is detectable rather
  than merely wrong.

What this module does *not* do is certify its own output. ``harness.historical_profile``
reads the written profile against the matrix and reports what does not hold, and
``harness.commands.historical_profile`` writes the reading a human checks. A tool
that both wrote a record and certified it would be judging its own output.

Constitutional standing: a deterministic author for a Tier 2A-adjacent harness
configuration. It evaluates no gate, invokes no Claude, reads no higher tier it
writes to, and coins no project fact: every value it writes is read from a
committed record. ``--check`` is a byte-equal replay.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

AUTHORITY_DIR = Path("docs/tier4_orchestration_state/msca_dn/authority")
MATRIX_REL = AUTHORITY_DIR / "equivalence_matrix_2025_2026-10-13.json"
INDEX_REL = AUTHORITY_DIR / "authority_source_index_2026-10-13.json"

#: The profile this one is the historical counterpart of. Read, never written.
CURRENT_PROFILE_REL = Path("harness/profiles/msca_dn_2026_default.json")
PROFILE_REL = Path("harness/profiles/msca_dn_2025_historical.json")

SCORECARD_REL = Path("harness/evaluator_scorecard_msca_dn.json")
HIST_WP_REL = Path(
    "docs/tier2b_topic_and_call_sources/work_programmes/msca/"
    "wp-2-msca-actions_horizon-2023-2025_en.pdf"
)
AF_V5_REL = Path("docs/tier2a_instrument_schemas/application_forms/msca/af_he-msca-dn_en.pdf")

PROFILE_ID = "msca_dn_2025_historical"
AUTHORED_ON = "2026-10-13"
TICKET = "V10 of plans/msca_dn_historical_validation_tickets.md"

SCHEMA = "pre_evaluation_profile/historical/1"


class HistoricalProfileError(RuntimeError):
    """A record this module refuses to derive a profile from."""


# --------------------------------------------------------------------------- #
# What sources what
#
# Each profile element names the matrix rows that establish its 2025 value, or
# the row that leaves it open. The ids are checked against the matrix: a row
# that is not there, or whose verdict cannot carry the use made of it, refuses.
# --------------------------------------------------------------------------- #

#: element -> the rows that source it. Every row here must be ``equivalent``,
#: ``differs`` or ``era_neutral``: those state what the 2025 rule was.
SOURCED_BY: dict[str, tuple[str, ...]] = {
    "criteria": ("CR-01", "CR-02"),
    "weights": ("WT-01", "SA-01"),
    "weighting_is_for_ranking": ("WT-02",),
    "individual_threshold": ("TH-01",),
    "overall_threshold": ("TH-02", "TH-03", "TH-06"),
    "score_maximum": ("TH-04",),
    "score_resolution": ("TH-05",),
    "score_levels": ("EI-01",),
    "scores_are_per_criterion": ("EI-03",),
    "option_tag_grammar": ("EI-04",),
    "implementation_mode": ("VA-01", "VA-02"),
    "structural_authority": ("SM-01", "SM-02", "SM-03"),
    "criterion_appendix_mapping": ("AM-01",),
}

#: element -> the row that leaves it open, and what the profile must say. An
#: ``unresolved`` row cannot source an element, so the element says so instead.
LIMITED_BY: tuple[tuple[str, str, str], ...] = (
    (
        "target_call",
        "CI-01",
        "The call's own identifier, opening and deadline are stated by the work programme the "
        "call was opened under. That this submission was entered into that call is declared by "
        "two records and evidenced by neither, so the binding is Assumed.",
    ),
    (
        "scorecard",
        "EI-02",
        "The scorecard is derived from the 2026 evaluation form, and every scoring rule it "
        "carries is sourced to a 2025 document by the rows above. Which version of the "
        "evaluation form the 2025 evaluators were given is not established: captures of the "
        "published address bracket the call window without closing it.",
    ),
)

#: Elements no call document of either year states, so the matrix carries them
#: as ``era_neutral`` and the profile declares them as the harness's own.
HARNESS_OWN: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "rubric_set",
        ("SA-02", "SA-03", "SA-05", "SA-06"),
        "The rubrics are this harness's grading instrument, not a rule of either call. No call "
        "document of either year states them, which is why the matrix carries them as era "
        "neutral rather than equivalent. They are unchanged from the 2026 profile, and that is "
        "a reuse of an instrument and not a finding that the 2025 call prescribed it.",
    ),
    (
        "assessed_text",
        ("SA-04",),
        "The text this profile is used to assess is a sanitised derivative produced after the "
        "2025 evaluation, not the text the 2025 evaluators read.",
    ),
)

#: Verdicts that may source a profile element.
SOURCING_VERDICTS: tuple[str, ...] = ("equivalent", "differs", "era_neutral")


# --------------------------------------------------------------------------- #
# Reading the records
# --------------------------------------------------------------------------- #


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise HistoricalProfileError(f"{path.as_posix()}: not in the tree")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows_by_id(matrix: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    for row in matrix["rows"]:
        if row["id"] in rows:
            raise HistoricalProfileError(f"{row['id']}: the matrix carries it twice")
        rows[row["id"]] = row
    return rows


def _refuse_unless_rows_can_source(rows: Mapping[str, Mapping[str, Any]]) -> None:
    """Refuse if a row cited as a source cannot be one, or is not there.

    An element sourced to an unresolved row would be claiming the matrix
    settled something it recorded as open, which is the one thing the matrix
    exists to prevent being done quietly.
    """
    for element, ids in SOURCED_BY.items():
        for row_id in ids:
            row = rows.get(row_id)
            if row is None:
                raise HistoricalProfileError(
                    f"{element}: the matrix has no row {row_id}"
                )
            if row["verdict"] not in SOURCING_VERDICTS:
                raise HistoricalProfileError(
                    f"{element}: row {row_id} is {row['verdict']} and cannot source an element"
                )
    for element, row_id, _ in LIMITED_BY:
        row = rows.get(row_id)
        if row is None:
            raise HistoricalProfileError(f"{element}: the matrix has no row {row_id}")
        if row["verdict"] != "unresolved":
            raise HistoricalProfileError(
                f"{element}: row {row_id} is {row['verdict']}, so the limitation this profile "
                "declares no longer matches the matrix; the element can be sourced instead"
            )
    for element, ids, _ in HARNESS_OWN:
        for row_id in ids:
            row = rows.get(row_id)
            if row is None:
                raise HistoricalProfileError(f"{element}: the matrix has no row {row_id}")
            if row["verdict"] != "era_neutral":
                raise HistoricalProfileError(
                    f"{element}: row {row_id} is {row['verdict']}, not era_neutral; it is a "
                    "rule of a call and must be sourced rather than declared the harness's own"
                )


def _refuse_unless_every_row_is_accounted_for(
    rows: Mapping[str, Mapping[str, Any]]
) -> None:
    """Refuse if a matrix row reaches no profile element.

    The matrix is the profile's whole source. A row nobody reads is either a
    rule this profile silently ignores or a row that should not be there, and
    both are decisions rather than omissions.
    """
    named = {r for ids in SOURCED_BY.values() for r in ids}
    named |= {row_id for _, row_id, _ in LIMITED_BY}
    named |= {r for _, ids, _ in HARNESS_OWN for r in ids}
    unread = sorted(set(rows) - named)
    if unread:
        raise HistoricalProfileError(
            "the matrix carries rows no profile element reads: " + ", ".join(unread)
        )


def _criteria(current: Mapping[str, Any], scorecard: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The three criteria, in the matrix's order, with the 2025 weights.

    Read from the scorecard the matrix sources, and shaped like the current
    profile's so one loader reads both.
    """
    by_id = {c["id"]: c for c in scorecard["criteria"]}
    out: list[dict[str, Any]] = []
    for spec in current["criteria"]:
        criterion = by_id.get(spec["id"])
        if criterion is None:
            raise HistoricalProfileError(
                f"{spec['id']}: the scorecard declares no such criterion"
            )
        out.append(
            {
                "id": spec["id"],
                "registry_criterion_id": spec["registry_criterion_id"],
                "section_ids": list(spec["section_ids"]),
                "weight_pct": criterion["weight_pct"],
                "threshold_score": criterion["threshold_score"],
            }
        )
    return out


def _target_call(matrix_rows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """The 2025 call, with the two halves of its status kept apart.

    The call exists and its dates are stated by a document of its own year.
    That this submission was entered into it is not, and collapsing the two
    into one status is what row CI-01 refuses to let the profile do.
    """
    row = matrix_rows["CI-01"]
    quotes = [c.get("quote", "") for c in row["citations"] if c.get("page")]
    return {
        "call_id": "HORIZON-MSCA-2025-DN-01",
        "topic_id": "HORIZON-MSCA-2025-DN-01-01",
        "opening": "2025-05-28",
        "deadline": "2025-11-25",
        "source_path": HIST_WP_REL.as_posix(),
        "source_page": 23,
        "label": "historical assessment of the submitted 2025 original",
        "the_call": {
            "declared_status": "Inferred",
            "basis": (
                "the work programme the call was opened under states the identifier, the "
                "opening date and the deadline on the page cited here. Inferred rather than "
                "Confirmed because no hash published by the issuing body vouches for that "
                "document's bytes."
            ),
            "quotes": quotes,
        },
        "the_binding": {
            "declared_status": "Assumed",
            "basis": (
                "two records declare that this submission was made to this call, and neither "
                "evidences it. Row CI-01 keeps that open."
            ),
            "matrix_row": "CI-01",
        },
    }


def _scoring(scorecard: Mapping[str, Any]) -> dict[str, Any]:
    """The scoring rules, each beside the rows that source it for 2025."""
    scoring = scorecard["scoring"]
    return {
        "scale": scoring["scale"],
        "score_maximum": 5,
        "individual_threshold": scoring["individual_threshold"],
        "overall_threshold": scoring["overall_threshold"],
        "overall_max": scoring["overall_max"],
        "total_formula": scoring["total_formula"],
        "weighting_is_for_ranking": scoring["weighting_source_quote"],
        "levels": dict(scoring["levels"]),
        "the_total_the_2025_form_printed": {
            "matrix_row": "TH-06",
            "what": (
                "The 2025 evaluation form prints an unweighted total out of 15 with an overall "
                "threshold of 10 points. This profile does not use it. The call's own work "
                "programme sets the threshold at 70% of the weighted total, and the recorded "
                "2025 result is a weighted total out of 100."
            ),
        },
        "the_resolution_conflict": {
            "matrix_row": "TH-05",
            "what": (
                "The work programme states one decimal place and the evaluation form of the "
                "call window states that half marks may be given. The recorded scores show "
                "which was applied. The conflict is not resolved for any other proposal."
            ),
        },
    }


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def render_profile(repo_root: Path) -> dict[str, Any]:
    """The historical profile, derived from the matrix and the records it cites."""
    matrix = _read_json(repo_root / MATRIX_REL)
    current = _read_json(repo_root / CURRENT_PROFILE_REL)
    scorecard = _read_json(repo_root / SCORECARD_REL)
    rows = _rows_by_id(matrix)

    _refuse_unless_rows_can_source(rows)
    _refuse_unless_every_row_is_accounted_for(rows)

    for rel in (HIST_WP_REL, AF_V5_REL):
        if not (repo_root / rel).is_file():
            raise HistoricalProfileError(f"{rel.as_posix()}: not in the tree")

    sourced = {
        element: {
            "matrix_rows": list(ids),
            "verdicts": [rows[r]["verdict"] for r in ids],
        }
        for element, ids in SOURCED_BY.items()
    }
    limitations = [
        {
            "element": element,
            "matrix_row": row_id,
            "verdict": rows[row_id]["verdict"],
            "limitation": wording,
        }
        for element, row_id, wording in LIMITED_BY
    ]
    harness_own = [
        {
            "element": element,
            "matrix_rows": list(ids),
            "why": wording,
        }
        for element, ids, wording in HARNESS_OWN
    ]

    return {
        "schema": SCHEMA,
        "profile_id": PROFILE_ID,
        "label": (
            "MSCA Doctoral Networks — 2025 historical pre-evaluation profile, authored "
            "from the equivalence matrix"
        ),
        "authored_on": AUTHORED_ON,
        "ticket": TICKET,
        "written_by": "tools/author_msca_dn_historical_profile.py",
        "advisory": True,
        "blocking": False,
        "purpose": (
            "Score the submitted 2025 original under the rules of its own call. Every element "
            "below either names the matrix rows that establish the 2025 rule, or declares what "
            "the matrix left open. An element that did neither would be the 2026 profile under "
            "another name."
        ),
        "review_state": "agent_drafted_pending_operator_review",
        "declared_status": "Inferred",
        "declared_status_note": (
            "Inferred, not Confirmed. Every rule here is sourced to a document of the 2025 "
            "call, and no document carries a hash published by its issuing body. The matrix "
            "declares no row Confirmed, and a profile cannot be more certain than the matrix "
            "it is authored from."
        ),
        "counterpart": {
            "path": CURRENT_PROFILE_REL.as_posix(),
            "profile_id": current["profile_id"],
            "sha256": _file_sha256(repo_root / CURRENT_PROFILE_REL),
            "rule": (
                "That profile is not edited by this ticket, and its own applicability question "
                "stays open. This one is a second profile beside it, not a replacement."
            ),
        },
        "authored_from": {
            "matrix": {
                "path": MATRIX_REL.as_posix(),
                "sha256": _file_sha256(repo_root / MATRIX_REL),
                "role": "tracked_input",
            },
            "source_index": {
                "path": INDEX_REL.as_posix(),
                "sha256": _file_sha256(repo_root / INDEX_REL),
                "role": "tracked_input",
            },
            "rule": (
                "Both are pinned by the sha256 of their bytes. A profile read beside a matrix "
                "that has moved is stale, and the check reports it rather than scoring under it."
            ),
        },
        # --- what harness.profile parses ---------------------------------- #
        "instrument": dict(current["instrument"]),
        "option_tag_grammar": dict(current["option_tag_grammar"]),
        "criteria": _criteria(current, scorecard),
        "registry_path": current["registry_path"],
        "scorecard": dict(current["scorecard"]),
        "rubric_set": dict(current["rubric_set"]),
        "criterion_appendix_mapping": dict(current["criterion_appendix_mapping"]),
        # --- what this profile adds --------------------------------------- #
        "structural_authority": {
            "path": AF_V5_REL.as_posix(),
            "version": "5.0",
            "sha256": _file_sha256(repo_root / AF_V5_REL),
            "why_this_one": (
                "The 2025 call's own application form, not the 2026 template the current "
                "profile names. Rows SM-01 and SM-02 measure the ten aspect headings and the "
                "Part B1 caps against it."
            ),
            "the_added_section": {
                "matrix_row": "SM-03",
                "what": (
                    "The 2026 template adds a Part B2 section the 2025 form does not have, so "
                    "the appendix mapping's rule excluding that section has no subject here. "
                    "The rule is kept and recorded as vacuous rather than deleted."
                ),
            },
            "origin_not_recorded": (
                "Nothing records where this form's bytes came from, and nothing establishes it "
                "was the version in force. The source index declares both unresolved, and the "
                "five rows citing it are Inferred for that reason."
            ),
        },
        "implementation_mode": current["implementation_mode"],
        "target_call": _target_call(rows),
        "scoring": _scoring(scorecard),
        "sourced_from_the_matrix": sourced,
        "declared_limitations": limitations,
        "the_harness_own_instruments": harness_own,
        "not_evidence_of": [
            "that the 2025 evaluators would score this text as this profile scores it",
            "that the harness's scoring method is correct",
            "that this profile is accepted. Acceptance is the operator's.",
        ],
        "authority_note": (
            "This profile confers no authority and closes no gate. It configures an "
            "out-of-band assessment. Loading it is not evidence that any assessment was run."
        ),
    }


def canonical_json_bytes(data: Any) -> bytes:
    """One byte sequence for one document, so ``--check`` can compare bytes."""
    return (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n").encode(
        "utf-8"
    )


def render_all(repo_root: Path) -> dict[str, bytes]:
    return {PROFILE_REL.as_posix(): canonical_json_bytes(render_profile(repo_root))}


def check(repo_root: Path) -> list[str]:
    """The paths whose committed bytes differ from a fresh derivation."""
    stale: list[str] = []
    for rel, body in render_all(repo_root).items():
        path = repo_root / rel
        if not path.is_file() or path.read_bytes() != body:
            stale.append(rel)
    return stale


def write(repo_root: Path) -> list[str]:
    written: list[str] = []
    for rel, body in render_all(repo_root).items():
        path = repo_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file() or path.read_bytes() != body:
            path.write_bytes(body)
            written.append(rel)
    return written


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the committed profile is not a byte-equal replay",
    )
    parser.add_argument("--repo-root", default=".", help="repository root (default: .)")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root)

    try:
        if args.check:
            stale = check(repo_root)
            if stale:
                for rel in stale:
                    print(f"stale: {rel}")
                return 1
            print("up to date")
            return 0
        written = write(repo_root)
        for rel in written:
            print(f"wrote: {rel}")
        print(f"{len(written)} file(s) written")
        if written:
            print("now check it and render its reading:")
            print("  py -3.10 -m harness.commands.historical_profile")
        return 0
    except HistoricalProfileError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
