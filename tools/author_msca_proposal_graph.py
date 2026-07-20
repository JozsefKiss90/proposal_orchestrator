#!/usr/bin/env python3
"""
tools/author_msca_proposal_graph.py — Milestone 2, ticket 8 authoring seed.

Deterministically transcribes the CURRENT, real, operator-confirmed project docs
into vault binding nodes + ``proposal_section`` nodes under
``MSCA/methodology_graph/`` (folders 11-19), so the milestone-2 compiler
(tickets 3 + 6) and the pack-from-graph deriver (ticket 7) have real content to
compile end-to-end (the "convergence lands with ticket 8" note the walking
skeletons recorded).

WHAT THIS IS (and is not)
-------------------------
A **one-time authoring aid**, not runtime code, not a skill, not the compiler.
The committed vault nodes it emits are the deliverable and become the
graph-native authoring surface.  It runs BEFORE the runtime, touches nothing the
DAG scheduler or gates read, and is subordinate to ``CLAUDE.md``.

ANTI-FABRICATION (CLAUDE.md §13.3, §10.5, Appendix B)
-----------------------------------------------------
It authors **no** evaluator-facing prose and invents **no** fact.  All
``proposal_section`` bodies (the Part B narrative — the deliverable prose) and
every structured domain field are lifted **verbatim** (UTF-8, byte-preserving)
from the existing authoritative ``docs/**`` artifacts.  The only script-composed
text is deterministic scaffolding on **source-only** nodes — the ``## Related``
wikilink blocks on Tier-3 nodes and the descriptive bodies on folder-17 budget
nodes — which interpolates *only* verbatim facts (amounts, the host coefficient,
node ids) and reaches no deliverable (folder 17 has no ``artifact_path``; the
compiler never reads these bodies).  The only derived *field* is the canonical
``evidence_strength`` enum, computed by a pure, status-**preserving** lookup that
never upgrades provenance:

    Tier-3 record.validation_status  ->  node.evidence_strength (canonical enum)
      Confirmed   -> source_grounded   (Appendix-B -> Confirmed)
      Inferred    -> synthesis         (Appendix-B -> Inferred)
      Assumed     -> unconfirmed       (no enum yields Assumed; honestly degraded
                                        to Unresolved, never upgraded; none today)
      Unresolved  -> unconfirmed       (Appendix-B -> Unresolved)

    proposal_section prose  ->  synthesis
      Drafted evaluator narrative is *synthesis over* the confirmed Tier-3/2B
      substrate, never a raw source fact; ``synthesis`` -> Inferred preserves
      each section's real ``overall_status: inferred`` and never dresses
      narrative as a ``source_grounded`` (Confirmed) fact (ticket-8 criterion 2).

The original descriptive provenance string (e.g. ``"source_grounded (methodology)
+ operator_confirmed (RQ2/RQ3/RQ8)"``) is preserved verbatim in a pass-through
``provenance_detail`` field so no information is lost and the ticket-10 cutover
has the full audit trail.

THE SPINE (ticket-8 criterion 3)
--------------------------------
The researcher/host/supervisor/partner spine (Dr. Rositsa Cholakova / ELTE /
Dr. András Jung / AgroVIR) is **operator-confirmed** in Tier-3
``consortium/roles.json`` (13B consolidation) and is referenced by the
``proposal_section`` prose this script lifts — so the graph carries the spine as
its real **Confirmed** state.  The methodology vault's ``08_partners/`` nodes are
left **unchanged** (ELTE Role etc. remain ``unconfirmed`` — the source-honest
"do not invent" posture): the methodology sources never named the spine, and that
truthful state is preserved.  No dual/fabricated partner nodes are created.

SOURCE DOCS (read-only)  ->  NODE TARGETS
-----------------------------------------
  architecture_inputs/objectives.json       -> 11_objectives/      (objective)
  architecture_inputs/outcomes.json         -> 12_outcomes/        (outcome)
  architecture_inputs/impacts.json          -> 13_impacts/         (impact)
  architecture_inputs/workpackage_seed.json -> 14_work_packages/   (work_package)
  architecture_inputs/milestones_seed.json  -> 15_timeline/        (timeline; id=milestone_id)
  architecture_inputs/risks.json            -> 16_risks/           (risk)
  phase7_budget_gate/unit_cost_budget.json  -> 17_budget/          (budget; source-only)
  tier5_.../proposal_sections/{slug}_section.json -> 19_proposal_sections/ (proposal_section)
  18_phase_gate_state/                      -> .gitkeep (docs_to_graph projector-owned)

Idempotent: same docs => byte-identical nodes.  Re-running overwrites the
folders-11-19 nodes from docs (correct while the graph still mirrors docs; after
graph-native edits diverge, the graph is authoritative — do not blindly re-run).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

# --------------------------------------------------------------------------- #
# Paths (repo-relative; this file lives at <repo>/tools/)
# --------------------------------------------------------------------------- #

REPO_ROOT = Path(__file__).resolve().parents[1]

# This one-time tool lives in tools/, so put the repo root on the import path and
# pull the CANONICAL runtime constants from runner/ rather than re-declaring them.
# The compiler derives its reserved-key set from the schema precisely so it can
# never drift; this script must not reintroduce that drift (code-review, Standards).
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runner.graph_compiler import RESERVED_FM_KEYS  # noqa: E402  (needs REPO_ROOT on sys.path)
from runner.graph_schema import EVIDENCE_TO_STATUS  # noqa: E402

VAULT = REPO_ROOT / "MSCA" / "methodology_graph"
ARCH = REPO_ROOT / "docs" / "tier3_project_instantiation" / "architecture_inputs"
SECTIONS = REPO_ROOT / "docs" / "tier5_deliverables" / "proposal_sections"
BUDGET = (
    REPO_ROOT
    / "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/unit_cost_budget.json"
)
ROLES = REPO_ROOT / "docs/tier3_project_instantiation/consortium/roles.json"

# --------------------------------------------------------------------------- #
# Status-preserving Appendix-B inverse (validation_status -> canonical enum)
# --------------------------------------------------------------------------- #

STATUS_TO_EVIDENCE: dict[str, str] = {
    "Confirmed": "source_grounded",
    "Inferred": "synthesis",  # representative of the two Inferred-yielding enums
    "Assumed": "unconfirmed",  # no enum yields Assumed — degrade to Unresolved (see below)
    "Unresolved": "unconfirmed",
}

# Drift guard: the chosen canonical enum must reproduce the declared status through
# the canonical Appendix-B lookup (runner.graph_schema.EVIDENCE_TO_STATUS), so a
# schema change surfaces here instead of silently drifting.  'Assumed' is exempt:
# no evidence_strength maps to Assumed (it is an operator-declared flip of
# Unresolved per the schema), so an Assumed record is honestly degraded to
# unconfirmed -> Unresolved rather than upgraded.
assert all(
    EVIDENCE_TO_STATUS[ev] == st
    for st, ev in STATUS_TO_EVIDENCE.items()
    if st != "Assumed"
), "STATUS_TO_EVIDENCE drifted from runner.graph_schema.EVIDENCE_TO_STATUS"

# Front-matter keys the compiler reserves / computes — never copied as record
# content (id/title/node_type/evidence_strength/tier/aliases are placed explicitly;
# validation_status is computed).  Imported from the compiler (not re-declared) so
# it can never drift and cannot clobber an explicitly-set field (code-review).
_SKIP_RECORD_KEYS = RESERVED_FM_KEYS

# Tier-3 collections: (source filename, collection_key, folder, node_type)
TIER3_COLLECTIONS = [
    ("objectives.json", "objectives", "11_objectives", "objective"),
    ("outcomes.json", "outcomes", "12_outcomes", "outcome"),
    ("impacts.json", "impacts", "13_impacts", "impact"),
    ("workpackage_seed.json", "work_packages", "14_work_packages", "work_package"),
    ("milestones_seed.json", "milestones", "15_timeline", "timeline"),
    ("risks.json", "risks", "16_risks", "risk"),
]

# Body cross-reference fields whose values are node ids (resolved via aliases).
# linked_deliverable_ids is intentionally excluded — deliverables are Phase-3
# seed forward-refs, not graph nodes, so linking them would only dangle.
_XREF_FIELDS = [
    "linked_objectives", "linked_outcomes", "linked_impacts", "linked_wp_ids",
    "linked_work_packages", "objectives_addressed", "affected_objectives",
    "affected_work_packages", "responsible_wp",
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sanitize_filename(text: str, cap: int = 90) -> str:
    """A filesystem-safe, deterministic filename fragment (Windows + POSIX)."""
    text = re.sub(r'[\\/:*?"<>|]', "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:cap].rstrip()


def _strip_meth_suffix(name: str) -> str:
    """``'Diagnostic Branch (METH-CORE-002)'`` -> ``'Diagnostic Branch'`` (wikilink target)."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()


def _dump_front_matter(fm: dict[str, Any]) -> str:
    """Serialise front-matter to a YAML block, key order preserved, unicode literal."""
    body = yaml.safe_dump(
        fm, sort_keys=False, allow_unicode=True, default_flow_style=False, width=4096
    )
    return f"---\n{body}---\n"


def _write_node(folder: Path, filename: str, fm: dict[str, Any], body: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    text = _dump_front_matter(fm) + "\n" + body.rstrip("\n") + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _methodology_basenames() -> set[str]:
    """Filename stems of existing *methodology* nodes (folders 00-10, 90, 99).

    These are the resolvable wikilink targets for ``source_vault_nodes`` refs.
    Binding folders (11-19) are excluded so the set is stable across idempotent
    re-runs.  A ``source_vault_nodes`` entry that does not resolve to one of these
    (e.g. ``'Risk Register R1'`` — a *row* of the METH-RISK-002 node, not a node)
    is rendered as faithful plain text rather than a dangling wikilink.
    """
    prefixes = ("11_", "12_", "13_", "14_", "15_", "16_", "17_", "18_", "19_")
    stems: set[str] = set()
    for md in VAULT.rglob("*.md"):
        if not md.relative_to(VAULT).as_posix().startswith(prefixes):
            stems.add(md.stem)
    return stems


def _links_block(record: dict[str, Any], resolvable: set[str]) -> str:
    """A deterministic '## Related' block: source vault nodes + id cross-refs.

    A ``source_vault_nodes`` reference becomes a ``[[wikilink]]`` only when it
    resolves to a real methodology node basename; otherwise the full original
    reference is kept as plain text (no dangling links introduced).  Id cross-refs
    ([[OBJ-1]] etc.) resolve via the aliases the binding nodes declare.
    """
    lines: list[str] = []
    svn = record.get("source_vault_nodes")
    if isinstance(svn, list) and svn:
        parts: list[str] = []
        for n in svn:
            stripped = _strip_meth_suffix(str(n))
            parts.append(f"[[{stripped}]]" if stripped in resolvable else str(n))
        lines.append("**Grounded in methodology nodes:** " + ", ".join(parts))
    xrefs: list[str] = []
    for field in _XREF_FIELDS:
        val = record.get(field)
        vals = val if isinstance(val, list) else ([val] if isinstance(val, str) else [])
        for v in vals:
            link = f"[[{v}]]"
            if link not in xrefs:
                xrefs.append(link)
    if xrefs:
        lines.append("**Related architecture nodes:** " + ", ".join(xrefs))
    return ("\n\n## Related\n\n" + "\n\n".join(lines) + "\n") if lines else ""


# --------------------------------------------------------------------------- #
# Tier-3 binding nodes (objectives / outcomes / impacts / WPs / milestones / risks)
# --------------------------------------------------------------------------- #


def author_tier3() -> dict[str, int]:
    counts: dict[str, int] = {}
    resolvable = _methodology_basenames()
    for filename, key, folder_name, node_type in TIER3_COLLECTIONS:
        obj = _load(ARCH / filename)
        records = obj[key]
        folder = VAULT / folder_name
        for record in records:
            rec_id = record.get("id") or record.get("milestone_id")
            if not rec_id:
                raise ValueError(f"{filename}: record with no id/milestone_id: {record!r}")
            title = record["title"]
            vstatus = record["validation_status"]
            if vstatus not in STATUS_TO_EVIDENCE:
                raise ValueError(f"{filename}:{rec_id}: unknown validation_status {vstatus!r}")
            evidence = STATUS_TO_EVIDENCE[vstatus]
            provenance_detail = record.get("evidence_strength", "")

            fm: dict[str, Any] = {
                "id": rec_id,
                "title": title,
                "node_type": node_type,
                "evidence_strength": evidence,
                "tier": "tier3",
                "aliases": [rec_id],
            }
            # Domain fields, verbatim, in source order (minus reserved/handled keys).
            for k, v in record.items():
                if k in _SKIP_RECORD_KEYS:
                    continue
                fm[k] = v
            fm["provenance_detail"] = provenance_detail

            lead = record.get("description") or record.get("verifiable_criterion") or title
            body = str(lead).rstrip() + _links_block(record, resolvable)

            fname = f"{rec_id} {_sanitize_filename(title)}.md"
            _write_node(folder, fname, fm, body)
        counts[folder_name] = len(records)
    return counts


# --------------------------------------------------------------------------- #
# Budget nodes (folder 17, source-only per the config)
# --------------------------------------------------------------------------- #


def author_budget() -> int:
    b = _load(BUDGET)
    folder = VAULT / "17_budget"
    deriv = b.get("derivation", {})
    provenance_detail = (
        "unit_cost deterministic derivation (CLAUDE.md §8.1 / C1), byte-equal "
        "replay checked; source: "
        "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/unit_cost_budget.json"
    )
    n = 0
    for line in b["line_items"]:
        line_id = line["line_id"]
        node_id = f"BUDGET-{line_id}"
        fm: dict[str, Any] = {
            "id": node_id,
            "title": f"Budget line — {line_id.replace('_', ' ')}",
            "node_type": "budget",
            # Conservative default: a MISSING status degrades to unconfirmed
            # (-> Unresolved), never up to source_grounded (the schema's fail-safe;
            # today every line is Confirmed).
            "evidence_strength": STATUS_TO_EVIDENCE.get(line.get("status"), "unconfirmed"),
            "tier": "tier3",
            "aliases": [node_id, line_id],
        }
        for k, v in line.items():
            fm[k] = v
        fm["formula"] = deriv.get("formula")
        fm["host_country"] = deriv.get("host_country")
        fm["provenance_detail"] = provenance_detail
        body = (
            f"MSCA-PF unit-cost budget line **{line_id}** "
            f"({'host-dependent' if line.get('host_dependent') else 'host-independent'}). "
            f"Derived deterministically as `{deriv.get('formula')}` over the confirmed "
            f"{deriv.get('confirmed_months')}-month European Fellowship at host country "
            f"{deriv.get('host_country')} "
            f"(coefficient {deriv.get('host_country_coefficient_percent')}%). "
            f"Amount: €{line.get('amount_eur')}."
        )
        _write_node(folder, f"{node_id}.md", fm, body)
        n += 1

    # Budget overview node (total + derivation context; source-only).  Its status
    # is DERIVED from the data, not hardcoded: source_grounded only when every line
    # is Confirmed with no unresolved or blocking components; otherwise unconfirmed.
    fully_confirmed = (
        all(li.get("status") == "Confirmed" for li in b["line_items"])
        and not b.get("unresolved_components")
        and not b.get("blocking_inconsistencies")
    )
    fm_total: dict[str, Any] = {
        "id": "BUDGET-total",
        "title": "Budget overview — unit-cost total",
        "node_type": "budget",
        "evidence_strength": "source_grounded" if fully_confirmed else "unconfirmed",
        "tier": "tier3",
        "aliases": ["BUDGET-total", "budget_total"],
        "instrument_type": b.get("instrument_type"),
        "budget_regime": b.get("budget_regime"),
        "total_eur": b.get("total_eur"),
        "confirmed_months": deriv.get("confirmed_months"),
        "host_country": deriv.get("host_country"),
        "host_country_coefficient_percent": deriv.get("host_country_coefficient_percent"),
        "unresolved_components": b.get("unresolved_components", []),
        "blocking_inconsistencies": b.get("blocking_inconsistencies", []),
        "source_refs": b.get("source_refs", []),
        "provenance_detail": provenance_detail,
    }
    body_total = (
        f"Total MSCA-PF unit-cost budget: **€{b.get('total_eur')}** over "
        f"{deriv.get('confirmed_months')} months at host country {deriv.get('host_country')} "
        f"(coefficient {deriv.get('host_country_coefficient_percent')}%). "
        f"Derived deterministically per CLAUDE.md §8.1 (unit-cost instruments), byte-equal "
        f"replay checked; no fabricated figures. Line items: "
        + ", ".join(f"[[BUDGET-{li['line_id']}]]" for li in b["line_items"])
        + "."
    )
    _write_node(folder, "BUDGET-total.md", fm_total, body_total)
    return n + 1


# --------------------------------------------------------------------------- #
# proposal_section nodes (folder 19; one node per Part B sub-section)
# --------------------------------------------------------------------------- #

_CORE_SECTION_KEYS = {
    "schema_id", "run_id", "artifact_status", "criterion", "sub_sections",
    "validation_status", "traceability_footer",
}


def author_proposal_sections() -> dict[str, int]:
    folder = VAULT / "19_proposal_sections"
    counts: dict[str, int] = {}
    for slug in ("excellence", "impact", "implementation"):
        section = _load(SECTIONS / f"{slug}_section.json")
        criterion = section["criterion"]
        primary_sources = section.get("traceability_footer", {}).get("primary_sources", [])
        extra_fields = {k: v for k, v in section.items() if k not in _CORE_SECTION_KEYS}
        # Provenance summary carried on every node for auditability (the graph model
        # is per-node; the section's fine-grained claim distribution is recorded here).
        vs = section.get("validation_status", {})
        claim_dist: dict[str, int] = {}
        for c in vs.get("claim_statuses", []):
            claim_dist[c.get("status")] = claim_dist.get(c.get("status"), 0) + 1

        subs = section["sub_sections"]
        for i, sub in enumerate(subs):
            sub_id = sub["sub_section_id"]
            node_id = f"PS-{slug}-{sub_id}"
            is_intro = "." not in str(sub_id)  # "1"/"2"/"3" are the section leads
            fm: dict[str, Any] = {
                "id": node_id,
                "title": sub["title"],
                "node_type": "proposal_section",
                "evidence_strength": "synthesis",
                "tier": "tier5",
                "section_slug": slug,
                "criterion": criterion,
                "sub_section_id": str(sub_id),
                "source_refs": primary_sources,
                "provenance_detail": (
                    f"Graph-authored (ticket 8) from "
                    f"docs/tier5_deliverables/proposal_sections/{slug}_section.json "
                    f"sub_section {sub_id}. Section overall_status="
                    f"{vs.get('overall_status')}; source claim distribution={claim_dist}. "
                    f"Per-node evidence_strength=synthesis: drafted evaluator narrative "
                    f"synthesises confirmed Tier-3/2B facts and never lands as a "
                    f"source_grounded fact."
                ),
            }
            # Section-specific required top-level fields (impact / implementation)
            # are declared once, on the section-lead node, and merged by the compiler.
            if is_intro and extra_fields:
                fm["section_extra_fields"] = extra_fields
            # word_count is (re)derived by the compiler from the body; page_estimate
            # is omitted (no page data to invent).  The body is the sub-section
            # content, verbatim.
            body = sub["content"]
            fname = f"{node_id} {_sanitize_filename(sub['title'], 60)}.md"
            _write_node(folder, fname, fm, body)
        counts[slug] = len(subs)
    return counts


# --------------------------------------------------------------------------- #
# Folder 18 (docs_to_graph projector-owned) — keep the folder, no node here.
# --------------------------------------------------------------------------- #


def ensure_phase_gate_folder() -> None:
    folder = VAULT / "18_phase_gate_state"
    folder.mkdir(parents=True, exist_ok=True)
    # Not a .md (the reader would fail closed on missing front-matter); a plain
    # keep-file so git tracks the otherwise projector-populated (gitignored) folder.
    (folder / ".gitkeep").write_text(
        "# docs_to_graph projector target (ticket 4). The projector writes\n"
        "# phase_gate_state mirror nodes here as PGS-*.md (gitignored, regenerable).\n"
        "# graph_to_docs (the compiler) never writes here — the D6 no-overlap invariant.\n",
        encoding="utf-8",
        newline="\n",
    )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> int:
    if not VAULT.is_dir():
        raise SystemExit(f"MSCA vault not found at {VAULT}")
    t3 = author_tier3()
    n_budget = author_budget()
    ps = author_proposal_sections()
    ensure_phase_gate_folder()

    print("[author] Tier-3 binding nodes:")
    for folder_name, n in t3.items():
        print(f"    {folder_name}: {n}")
    print(f"[author] 17_budget: {n_budget} budget nodes")
    print("[author] 19_proposal_sections:")
    for slug, n in ps.items():
        print(f"    {slug}: {n} sub-section nodes")
    total = sum(t3.values()) + n_budget + sum(ps.values())
    print(f"[author] total authored nodes: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
