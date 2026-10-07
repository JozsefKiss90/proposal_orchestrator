"""The fidelity register's declared half — the operator's durable input (R01).

The MSCA-DN fidelity register has two halves (spec decision 9). The *derived*
half is measured from the sanitised PDF by ``tools/import_external_proposal.py``;
the *declared* half is the operator's per-sub-section statement of presence and
transformation. Both halves live in one file, and that file is rendered in full
by ``tools/author_msca_dn_workspace.render_register`` on every authoring run.

The problem this module solves
------------------------------
Before R01 the renderer hard-coded ``declared.sub_sections`` as an empty list,
so a declaration typed into the register was overwritten by the next run of
either tool and failed their byte-equal ``--check``. The declared half had no
durable home.

The ownership boundary
----------------------
The tools own every measured and derived field of the register: the provenance
header's hashes and page counts, the whole derived half, and the revision
re-checks. The operator owns ``declared.sub_sections`` and nothing else. The
tools carry those rows through **unchanged** — no field is added to a row, none
is renamed, and none is interpreted. Only the row *order* is imposed, from the
derived inventory, so the rendering is canonical whatever order the operator
typed.

The mechanism: a durable input, one file per revision
-----------------------------------------------------
Declarations are read from

    docs/tier3_project_instantiation/source_materials/msca_dn/declarations/<revision_id>.json

a file the operator authors and the tools never write. A register is therefore
reproducible from documented inputs (CLAUDE.md §9.5): delete it, re-run the
tool, and the declared half comes back from this input. Reading the register's
own declared half back instead would have made the artifact its own source and
lost every declaration on a rebuild.

The file holds the record type, the revision it declares, and the table::

    {
      "record_type": "fidelity_declarations",
      "revision_id": "resolved_fixes",
      "sub_sections": [
        {"sub_section_id": "2.1",
         "presence": {"value": "...", "basis": "..."},
         "transformation": {"value": "...", "basis": "..."}}
      ]
    }

``presence`` and ``transformation`` are independent fields: a present but
heavily sanitised sub-section is not an absent one. Any further field the
operator adds — evidence, reviewer, ``declared_status`` — travels with the row.

What this module deliberately does not require
----------------------------------------------
A row needs a ``sub_section_id`` the revision's derived half lists, and both
fields stating something. It is **not** required to carry a ``basis`` or a
``declared_status``, unlike the operator file of
:mod:`runner.working_assumptions`, which pins both. The reason is scope: R01
owns retention and R04 owns what a declaration must say, including how the
three fidelity claims are separated and which status each carries. Tightening
the contract here would decide R04's format before the operator has. A row
with no basis is therefore carried into the register as written, and reads
there as an unattributed operator statement.

Missing-input behaviour
-----------------------
No file for a revision means **no declarations**, and the register renders the
same empty declared half it carried before R01, byte for byte. That is the
state of both committed registers today and it is a valid state pending review.

A file that exists but is malformed is **refused**, and nothing is written. An
empty ``sub_sections`` table in a present file is not malformed.

Revision-specificity
--------------------
The file name and the body's ``revision_id`` must agree, and a revision reads
only its own file. One revision's declarations can never reach another
revision's register, because each register renders from its own input.

The guard against silent loss
-----------------------------
The tools render the register in full, so a sub-section the register declares
and the input does not would vanish on the next write. Two acts produce that
state, and the input sha256 the register records tells them apart:

* a **withdrawal** — the operator removed the row from the input, so the
  register records older input bytes than the input now has, the input is the
  newer statement, and the write proceeds;
* **typing into the output** — beside the input the register was rendered
  from, or with no input at all. The write is refused, naming the rows and
  the input to move them to.

Withdrawing every declaration is an input holding an empty table, never a
deleted input: a deleted input cannot be told from a lost one. A sub-section
the input does declare may differ freely from the register's copy, since the
input owns it and the register is only stale.

Both tools run the guard before their first write, and the renderer runs it
again when it reaches each register. So ``--check`` can exit 1 with a refusal
rather than a staleness list. It stays read-only either way, and the refusal
is the more useful answer: it says where the declarations belong.

Constitutional standing: a reader for an authoring tool. It evaluates no gate,
invokes no Claude, writes nothing, and coins no ``schema_id``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

#: Where the operator's declaration inputs live, one file per revision: a
#: directory beside the registers themselves, under the case's source materials
#: (``tools.author_msca_dn_workspace.SOURCE_DIR_REL``, which this module cannot
#: import without a cycle; the test asserts the two agree).
DECLARATIONS_DIR_REL: Path = Path(
    "docs/tier3_project_instantiation/source_materials/msca_dn/declarations"
)

#: The ``record_type`` a declaration input must carry.
DECLARATIONS_RECORD_TYPE = "fidelity_declarations"

#: The two independent fields a declaration states per sub-section (decision 9).
REQUIRED_FIELDS: tuple[str, ...] = ("presence", "transformation")

#: Where the declared half sits in the register. This module owns that half,
#: so it owns the two key names; the renderer takes them from here.
DECLARED_HALF_KEY = "declared"
SUB_SECTIONS_KEY = "sub_sections"
INPUT_BLOCK_KEY = "declaration_input"


class FidelityDeclarationsError(Exception):
    """Refusal: a declaration input is malformed, misfiled, or would be lost."""


def declarations_rel(revision_id: str) -> Path:
    """The relative path of *revision_id*'s declaration input."""
    return DECLARATIONS_DIR_REL / f"{revision_id}.json"


@dataclass(frozen=True)
class Declarations:
    """One revision's operator declarations, as read from its input."""

    revision_id: str
    rows: tuple[dict[str, Any], ...]
    path_rel: Optional[str]
    """The input's path, or ``None`` when no input exists for this revision."""
    sha256: Optional[str]
    """The input's bytes, so the register names what it carried."""

    @property
    def supplied(self) -> bool:
        """Whether an input file exists, empty table included."""
        return self.path_rel is not None


def _refuse(rel: Path, message: str) -> FidelityDeclarationsError:
    return FidelityDeclarationsError(f"{rel.as_posix()}: {message}")


def _stated(value: Any) -> bool:
    """Whether a declaration field states something: a non-blank value."""
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list)):
        return bool(value)
    return value is not None


def _check_row(rel: Path, index: int, row: Any, seen: set[str]) -> dict[str, Any]:
    where = f"sub_sections[{index}]"
    if not isinstance(row, dict):
        raise _refuse(rel, f"{where} must be a JSON object, found {type(row).__name__}")
    sub_section_id = row.get("sub_section_id")
    if not isinstance(sub_section_id, str) or not sub_section_id.strip():
        raise _refuse(rel, f"{where} needs a non-blank 'sub_section_id' string")
    for field_name in REQUIRED_FIELDS:
        if field_name not in row:
            raise _refuse(rel, f"{where} ({sub_section_id}) needs a {field_name!r} field")
        if not _stated(row[field_name]):
            raise _refuse(
                rel, f"{where} ({sub_section_id}) states nothing under {field_name!r}"
            )
    if sub_section_id in seen:
        raise _refuse(rel, f"{where}: sub-section {sub_section_id!r} is declared twice")
    seen.add(sub_section_id)
    return row


def _read_json(path: Path, rel: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise _refuse(rel, f"is not valid JSON ({exc})") from exc


def load_declarations(repo_root: Path, revision_id: str) -> Declarations:
    """*revision_id*'s declarations, or the empty declaration when none exists.

    Refuses a present-but-malformed input. Nothing is written here, so a
    refusal always leaves the register as it was.
    """
    rel = declarations_rel(revision_id)
    path = repo_root / rel
    if not path.is_file():
        return Declarations(revision_id=revision_id, rows=(), path_rel=None, sha256=None)
    data = _read_json(path, rel)
    if not isinstance(data, dict):
        raise _refuse(rel, f"must hold a JSON object, found {type(data).__name__}")
    record_type = data.get("record_type")
    if record_type != DECLARATIONS_RECORD_TYPE:
        raise _refuse(
            rel, f"record_type must be {DECLARATIONS_RECORD_TYPE!r}, found {record_type!r}"
        )
    declared_revision = data.get("revision_id")
    if declared_revision != revision_id:
        raise _refuse(
            rel,
            f"declares revision_id {declared_revision!r} but is filed under {revision_id!r}; "
            "declarations are revision-specific and are never carried across revisions",
        )
    rows = data.get("sub_sections")
    if not isinstance(rows, list):
        raise _refuse(
            rel,
            "needs a 'sub_sections' list (an empty list is a valid, undeclared state); "
            f"found {type(rows).__name__}",
        )
    seen: set[str] = set()
    checked = tuple(_check_row(rel, i, row, seen) for i, row in enumerate(rows))
    return Declarations(
        revision_id=revision_id,
        rows=checked,
        path_rel=rel.as_posix(),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def resolve_rows(
    declarations: Declarations, inventory_ids: Sequence[str]
) -> tuple[dict[str, Any], ...]:
    """*declarations*' rows in the derived inventory's order.

    A declared sub-section the revision's derived half does not list is a
    refusal: the operator declared something this revision has no measurement
    for. A sub-section with no declaration is left out, since a partial
    declaration is a legitimate state while review is open.
    """
    order = {sub_section_id: i for i, sub_section_id in enumerate(inventory_ids)}
    rel = declarations_rel(declarations.revision_id)
    for row in declarations.rows:
        if row["sub_section_id"] not in order:
            raise _refuse(
                rel,
                f"declares sub-section {row['sub_section_id']!r}, which is not in the derived "
                f"inventory of revision {declarations.revision_id!r}",
            )
    return tuple(sorted(declarations.rows, key=lambda row: order[row["sub_section_id"]]))


def input_block(
    declarations: Declarations, rows: Sequence[dict[str, Any]]
) -> Optional[dict[str, Any]]:
    """What the register records about the input it carried, or ``None``.

    ``None`` when nothing was supplied, so a register with no declarations
    keeps the bytes it had before R01.
    """
    if not declarations.supplied:
        return None
    return {
        "path": declarations.path_rel,
        "sha256": declarations.sha256,
        "revision_id": declarations.revision_id,
        "declared_sub_sections": len(rows),
        "basis": (
            "the operator's durable declaration input for this revision, carried through "
            "unchanged and ordered by the derived inventory. The authoring tools own the "
            "measured half and never author or edit a declaration."
        ),
    }


@dataclass(frozen=True)
class RegisterDeclaredHalf:
    """What the register on disk holds in its declared half.

    This module owns that half, including where it sits in the file, so it is
    the one place that reads it back. Nothing else here reads a register.
    """

    sub_section_ids: tuple[str, ...]
    input_sha256: Optional[str]
    """The input bytes this half was rendered from, as the half records them."""


def read_declared_half(repo_root: Path, register_rel: Path) -> RegisterDeclaredHalf:
    """*register_rel*'s declared half, or the empty one when it is absent."""
    empty = RegisterDeclaredHalf(sub_section_ids=(), input_sha256=None)
    register = repo_root / register_rel
    if not register.is_file():
        return empty
    data = _read_json(register, register_rel)
    half = data.get(DECLARED_HALF_KEY) if isinstance(data, dict) else None
    if not isinstance(half, dict):
        return empty
    rows = half.get(SUB_SECTIONS_KEY)
    block = half.get(INPUT_BLOCK_KEY)
    recorded = block.get("sha256") if isinstance(block, dict) else None
    return RegisterDeclaredHalf(
        sub_section_ids=tuple(
            row["sub_section_id"]
            for row in (rows if isinstance(rows, list) else [])
            if isinstance(row, dict) and isinstance(row.get("sub_section_id"), str)
        ),
        input_sha256=recorded if isinstance(recorded, str) else None,
    )


def guard_against_silent_loss(
    repo_root: Path, register_rel: Path, declarations: Declarations
) -> None:
    """Refuse to render over a declaration the input would not bring back.

    The tools render the register in full, so whatever the declared half holds
    is replaced by the input's rows. A sub-section the register declares and
    the input does not would vanish on the next write. Two different acts
    produce that state, and the register's own record of the input bytes it
    was rendered from tells them apart:

    * The operator **withdrew** the row, by editing the input. The register
      then records a different input sha256 than the input now has, so the
      input is the newer statement and the write proceeds.
    * The operator **typed into the output**, beside the input the register was
      rendered from, or with no input at all. The recorded sha256 matches, or
      there is none. The write is refused, naming the rows and the input.

    Withdrawing every declaration is an input holding an empty table, never a
    deleted input: a deleted input cannot be told from a lost one.
    """
    half = read_declared_half(repo_root, register_rel)
    declared_here = {row["sub_section_id"] for row in declarations.rows}
    orphaned = [sid for sid in half.sub_section_ids if sid not in declared_here]
    if not orphaned:
        return
    input_is_newer = (
        declarations.supplied
        and half.input_sha256 is not None
        and half.input_sha256 != declarations.sha256
    )
    if input_is_newer:
        return
    rel = declarations_rel(declarations.revision_id)
    behind = (
        f"{rel.as_posix()} does not declare them"
        if declarations.supplied
        else "no declaration input stands behind them"
    )
    raise FidelityDeclarationsError(
        f"{register_rel.as_posix()} declares sub-section(s) {', '.join(orphaned)} under "
        f"'{DECLARED_HALF_KEY}.{SUB_SECTIONS_KEY}' and {behind}. The authoring tools render "
        f"this file in full, so writing it would erase them. Add them to {rel.as_posix()} "
        f"(record_type {DECLARATIONS_RECORD_TYPE!r}, revision_id "
        f"{declarations.revision_id!r}) and re-run. To withdraw a declaration, remove it "
        "from that input rather than from the register."
    )


def validate_inputs(repo_root: Path, revisions: Iterable[tuple[str, Path]]) -> None:
    """Load and guard the declaration input of each ``(revision_id, register)``.

    Called by a tool before its first write. The renderer loads and guards
    again when it reaches each register; that second pass is what protects a
    tool whose writes start before every register is rendered.
    """
    for revision_id, register_rel in revisions:
        guard_against_silent_loss(
            repo_root, register_rel, load_declarations(repo_root, revision_id)
        )


def declared_half(
    repo_root: Path, revision_id: str, register_rel: Path, inventory_ids: Iterable[str]
) -> tuple[tuple[dict[str, Any], ...], Optional[dict[str, Any]]]:
    """The rendered rows and input block of *revision_id*'s declared half.

    One call for the renderer: load, guard, resolve against the inventory.
    """
    declarations = load_declarations(repo_root, revision_id)
    guard_against_silent_loss(repo_root, register_rel, declarations)
    rows = resolve_rows(declarations, tuple(inventory_ids))
    return rows, input_block(declarations, rows)
