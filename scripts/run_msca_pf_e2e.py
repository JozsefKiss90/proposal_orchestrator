#!/usr/bin/env python
"""Ticket 13 — reproducible MSCA-PF end-to-end run driver (α / β).

This is the **runnable live path** for the milestone's definition of done
(D14).  It drives a full-DAG MSCA-PF run in two modes and captures the
non-deterministic drafting once (``section_drafts/``, §9.5 / W2), so the
deterministic half can be replayed with zero LLM calls by the CI harness
(``tests/runner/test_e2e_msca_pf_run.py``).

    Live run  →  proves the CLAIM (decomposed drafting fixes the ~10× length
                 shortfall; the honest block / conscious green work end-to-end).
    CI harness →  protects the GUARANTEES (byte-equal assembly, byte-equal
                 budget, W1, α-blocks / β-greens) on the captured fixtures.

The two are never conflated: this script makes live ``claude`` calls and is
**out of CI**; the harness makes none.

Modes
-----
α (honest Tier 3, spine Unresolved):
    The full governed DAG runs Phase 1 live, then **honest-blocks at Phase 2**:
    the semantic scope-alignment gate (``no_unresolved_scope_conflicts``)
    refuses to proceed while the researcher / host / supervisor spine is
    Unresolved, enumerating SCL-01..04 (geographic placement, career
    development plan, joint application, 6/8 expected outcomes Assumed).  This
    honest block is a **correct terminal state** (§12.4 / §15), not a failure to
    be "fixed" green.  It is preserved separately (tag ``alpha-honest-block``).

    (An MSCA-PF concept is spine-dependent at the *semantic* level — you cannot
    scope-align a fellowship without knowing the fellow, host and supervisor —
    so the block lands at Phase 2, earlier than the Phase-7 budget gate.  The β
    declaration substrate (ticket 15) reaches only Phase 7 + Phase 8, so
    declaring the spine does not unblock Phase 2; that gap is a milestone-2
    ticket.  See ``decision_log/synthetic-spine-demo-override_2026-07-13.json``.)

β (SYN-SPINE-01 — synthetic spine under the §3 operator override):
    With the identity spine fabricated into Tier 3 as **Confirmed** (a scoped,
    logged, reversible §3 human override — NOT engine fabrication), the scope
    conflicts resolve, phases 2-6 pass, and the host country (HU) is Confirmed,
    so ``gate_09`` resolves the unit-cost coefficient **without**
    ``working_assumptions.json``.  This stage then drafts Phase 8 live via
    decomposed per-sub-section calls, the assembler composes them, the drafting
    gates green, and the assembled Part B is exported to ``.docx`` — carrying a
    visible ``SYNTHETIC DEMO — NOT FOR SUBMISSION`` marker.  This stage still
    writes a ``working_assumptions.json`` (harmless: the host is already
    Confirmed in Tier 3, so no declaration is consulted).

Transport
---------
All live calls route through the local ``claude`` CLI (Max-authenticated) via
the ``CLAUDE_REFERENCE`` preset — no Bedrock/IAM.  The model the CLI receives
is the runtime's hardcoded ``claude-opus-4-8`` (valid on the local CLI); the
Bedrock-style model id in ``.env`` is never used on this path.

Usage
-----
    python scripts/run_msca_pf_e2e.py alpha --run-id msca-pf-e2e
    python scripts/run_msca_pf_e2e.py beta  --run-id msca-pf-e2e   # same run_id

The ``beta`` stage continues the SAME run_id the ``alpha`` stage established
(Phases 1-6 released), so no cross-run bootstrap / freshness threading is
needed: β only re-runs the budget gate and Phase 8.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure the repo root is importable when run as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from runner.decomposed_drafting import draft_section_decomposed  # noqa: E402
from runner.phase8_canonical_pack import (  # noqa: E402
    build_phase8_canonical_reference_pack,
)
from runner.section_assembler import VALID_SLUGS  # noqa: E402

_WA_REL = "docs/tier3_project_instantiation/working_assumptions.json"
_BUDGET_REL = (
    "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/"
    "unit_cost_budget.json"
)
_FIXTURES_DIR = "tests/fixtures/e2e_msca_pf"
_SLUG_ORDER = ("excellence", "impact", "implementation")

# β declarations: host country + fellowship duration.  These are demonstration
# working assumptions, NOT confirmed project commitments; each is surfaced as
# Assumed and W1-checked.  ELTE is deliberately NOT declared (the confirmation
# checklist refutes it).
_BETA_DECLARATIONS = {
    "_operator_note": (
        "TICKET 13 β RUN — operator-declared working assumptions that turn the "
        "honest α block into a conscious β green. Each is Assumed, never "
        "Confirmed; W1 (gate_10a/b/c) requires every Assumed claim to trace "
        "here, and the Phase-7 budget deriver reads host_country + "
        "project_duration_months. Demonstration assumptions, not commitments."
    ),
    "record_type": "working_assumptions",
    "provenance_class": "manually_placed",
    "declarations": [
        {
            "key": "host_country",
            "value": "BE",
            "declared_by": "operator (ticket-13 beta run)",
            "declared_on": "2026-07-14T00:00:00Z",
            "rationale": (
                "Host organisation assumed in Belgium (country-correction "
                "coefficient 100%). One host declaration resolves BOTH the "
                "Phase-7 living-allowance coefficient AND Assumed HOST identity "
                "claims (D11/D12)."
            ),
            "checklist_ref": "HOST",
        },
        {
            "key": "project_duration_months",
            "value": 24,
            "declared_by": "operator (ticket-13 beta run)",
            "declared_on": "2026-07-14T00:00:00Z",
            "rationale": (
                "24-month standard European Fellowship duration (working "
                "assumption); resolves the confirmed-months budget line."
            ),
            "checklist_ref": "DURATION",
        },
    ],
}


def _env() -> dict[str, str]:
    """Environment forcing the local claude CLI transport (no Bedrock/IAM)."""
    env = dict(os.environ)
    env["ORCHESTRATOR_TRANSPORT_PRESET"] = "CLAUDE_REFERENCE"
    return env


def _run_runner(repo_root: Path, run_id: str, *extra: str) -> int:
    """Invoke ``python -m runner`` with the given args; stream output."""
    cmd = [sys.executable, "-m", "runner", "--run-id", run_id, "--verbose", *extra]
    print(f"\n$ {' '.join(cmd)}\n", flush=True)
    return subprocess.run(cmd, cwd=repo_root, env=_env()).returncode


def _snapshot(repo_root: Path, mode: str) -> None:
    """Copy the mode's fixture-relevant artifacts into the CI fixtures tree."""
    dst = repo_root / _FIXTURES_DIR / mode
    dst.mkdir(parents=True, exist_ok=True)
    budget = repo_root / _BUDGET_REL
    if budget.is_file():
        shutil.copy2(budget, dst / "unit_cost_budget.json")
    if mode == "beta":
        drafts_root = (
            repo_root / "docs/tier4_orchestration_state/phase_outputs/"
            "phase8_drafting_review/section_drafts"
        )
        for slug in VALID_SLUGS:
            src = drafts_root / slug
            if src.is_dir():
                shutil.copytree(src, dst / "section_drafts" / slug, dirs_exist_ok=True)
        for slug in _SLUG_ORDER:
            sec = (
                repo_root / "docs/tier5_deliverables/proposal_sections/"
                f"{slug}_section.json"
            )
            if sec.is_file():
                shutil.copy2(sec, dst / f"{slug}_section.json")
    print(f"[snapshot] {mode} fixtures -> {dst.relative_to(repo_root)}")


def run_alpha(repo_root: Path, run_id: str) -> int:
    """α: full DAG, no declarations → honest block at the budget gate."""
    wa = repo_root / _WA_REL
    if wa.exists():
        wa.unlink()  # α must have no working_assumptions.json
    print("=== α (no declarations): expect honest block at gate_09 ===")
    rc = _run_runner(repo_root, run_id)  # full DAG
    _snapshot(repo_root, "alpha")
    budget = repo_root / _BUDGET_REL
    if budget.is_file():
        data = json.loads(budget.read_text("utf-8"))
        print(
            f"[α] budget gate_pass_declaration="
            f"{data.get('gate_pass_declaration')!r}  "
            f"unresolved={data.get('unresolved_components')}"
        )
    # A non-zero exit code IS the honest block (a correct terminal state).
    print(f"[α] run exit code = {rc} (non-zero = honest block = PASS)")
    return 0


def run_beta(repo_root: Path, run_id: str) -> int:
    """β: declare host+duration → budget passes → Phase 8 drafts live → .docx."""
    print("=== β (host + duration declared): expect all-green Part B ===")
    (repo_root / _WA_REL).write_text(
        json.dumps(_BETA_DECLARATIONS, indent=2), encoding="utf-8"
    )
    print(f"[β] wrote {_WA_REL}")

    # 1. Re-run the budget gate with the declarations present → gate_09 pass.
    if _run_runner(repo_root, run_id, "--phase", "7") != 0:
        print("[β] budget gate did not pass; aborting β")
        return 1

    # 2. Regenerate the canonical reference pack (Tier 3 confirmed + declared),
    #    so the live drafter can ground canonical terms in it.
    build_phase8_canonical_reference_pack(repo_root, run_id)

    # 3. Capture: live decomposed drafting -> section_drafts/<slug>/ (§9.5).
    for slug in _SLUG_ORDER:
        print(f"[β] live decomposed drafting: {slug}")
        paths = draft_section_decomposed(run_id, repo_root, slug)
        print(f"    wrote {len(paths)} draft file(s)")

    # 4. Governed Phase-8 replay: assemble captured drafts + audit + gates.
    rc = _run_runner(repo_root, run_id, "--phase", "8")

    # 5. Export the assembled Part B to .docx.
    _run_runner(repo_root, run_id, "--phase", "8", "--export-docx")

    _snapshot(repo_root, "beta")
    print(f"[β] Phase-8 run exit code = {rc} (0 = all-green Part B)")
    return rc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["alpha", "beta"])
    parser.add_argument("--run-id", default="msca-pf-e2e")
    args = parser.parse_args(argv)
    repo_root = _REPO_ROOT
    if args.mode == "alpha":
        return run_alpha(repo_root, args.run_id)
    return run_beta(repo_root, args.run_id)


if __name__ == "__main__":
    sys.exit(main())
