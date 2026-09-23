#!/usr/bin/env python3
"""LG-1 — Coarse claim ledger, measured.

Deterministic measurement of the claim-ledger granularity gap between the two
generations of the same three Part B sections:

* **graph-sourced** (current ``docs/tier5_deliverables/proposal_sections/*.json``,
  ``run_id=msca-pf-graph-01``) — the milestone-2 compiler emits one node-level
  ``proposal_section`` claim per sub-section (a "table of contents" ledger); and
* **drafter-era** — the granular per-assertion ledger the monolithic drafter
  produced, preserved byte-for-byte in the E4 regression golden baselines
  (``harness/regression_baselines/*.golden.json``, frozen 2026-07-21).

The prose under both ledgers is **byte-identical** (verified here per
sub-section), so the ledger is the only variable and the cardinality deficit is
exact rather than confounded by content drift.

This composes existing harness primitives only — E4's deterministic golden-set
comparison (:mod:`harness.regression`), E2's claim loader
(:mod:`harness.status_faithfulness`), and E3's prose surface
(:mod:`harness.claim_ledger` / :mod:`harness.materiality`). It lives in the
out-of-band harness package (not ``scripts/``, which must stay harness-free) and
runs **offline, with no judge and no DAG run**: the judge-scored layers of E2
(per-claim faithfulness) and E3 (semantic decomposition + coverage) require an
independent, non-Claude judge endpoint, which is not configured under this repo's
subscription-only ``claude_cli`` transport (the harness structurally refuses the
drafter's own model for grader-generator independence). With byte-identical prose
the deterministic evidence below is sufficient for the accept-or-enrich decision:
the assertion *denominator* both ledgers must attribute is held constant, so the
graph ledger's cardinality deficit is a lower bound on E3's escaped-material-
assertion count.

``build_report`` is pure (returns the report dict, writes nothing); only the CLI
``main`` writes, to an operator-controlled ``--out`` path.

Usage::

    py -3.10 -m harness.ledger_granularity [--out PATH] [--repo-root DIR]

Writes a JSON report (default: the decision-log directory) and prints an
ASCII summary table.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

from harness.claim_ledger import (
    chunk_prose,
    dedup_ledger_claims,
    load_section_prose,
)
from harness.regression import (
    DEFAULT_GOLDEN_DIR,
    DEFAULT_SECTIONS_DIR,
    compare_to_golden_set,
    load_fingerprint,
    load_golden_set,
)
from harness.status_faithfulness import load_section_claims
from runner.atomic_write import atomic_write_json

#: Sentence-terminator run — a self-contained deterministic proxy for the
#: material-assertion *surface*.  Deliberately NOT ``materiality._sentences``,
#: which is privately tuned for negative-candidate seeding (it drops sub-40-char
#: sentences and headings) and would silently couple this measurement to an
#: unrelated threshold.
_SENTENCE_END_RE = re.compile(r"[.!?]+(?:\s|$)")

SECTIONS: tuple[str, ...] = ("excellence", "impact", "implementation")

DEFAULT_OUT_REL = (
    "docs/tier4_orchestration_state/decision_log/"
    "lg1_ledger_granularity_measurement_2026-07-27.json"
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _count_sentences(text: str) -> int:
    """Deterministic, self-contained sentence-surface proxy (see _SENTENCE_END_RE)."""
    return len(_SENTENCE_END_RE.findall(text))


def _status_partition(statuses: list[str]) -> dict[str, int]:
    part: dict[str, int] = {}
    for s in statuses:
        key = (s or "").strip().lower() or "<empty>"
        part[key] = part.get(key, 0) + 1
    return part


def measure_section(
    slug: str, sections_dir: Path, golden_dir: Path
) -> dict[str, Any]:
    """Deterministic per-section measurement of the two ledgers over one prose."""
    section_path = sections_dir / f"{slug}_section.json"
    golden_path = golden_dir / f"{slug}_section.golden.json"

    # --- Graph-sourced ledger (current docs section) ---
    graph_claims = load_section_claims(section_path)
    graph_statuses = [c.status for c in graph_claims]
    graph_dedup = dedup_ledger_claims(graph_claims)

    # --- Drafter-era ledger (E4 golden baseline; typed, fail-closed loader) ---
    golden_fp = load_fingerprint(golden_path)
    drafter_statuses = [c.status for c in golden_fp.claims]
    drafter_n = len(golden_fp.claims)

    # --- Prose surface (identical for both ledgers; verified below) ---
    prose = load_section_prose(section_path)
    total_chunks = sum(len(chunk_prose(ss)) for ss in prose)
    total_sentences = sum(_count_sentences(ss.content) for ss in prose)
    total_words = sum(len(ss.content.split()) for ss in prose)
    total_chars = sum(len(ss.content) for ss in prose)

    # --- Prose byte-identity: graph sub-section content vs golden content hash ---
    golden_sub_hash = {
        s.sub_section_id: s.content_sha256 for s in golden_fp.sub_sections
    }
    per_sub_identity = []
    all_identical = True
    for ss in prose:
        cur_hash = _sha256(ss.content)
        gold_hash = golden_sub_hash.get(ss.sub_section_id)
        identical = cur_hash == gold_hash
        all_identical = all_identical and identical
        per_sub_identity.append(
            {
                "sub_section_id": ss.sub_section_id,
                "identical": identical,
                "current_content_sha256": cur_hash,
                "golden_content_sha256": gold_hash,
            }
        )

    n_sub = len(prose)
    graph_n = len(graph_claims)
    ratio = (drafter_n / graph_n) if graph_n else None

    return {
        "sub_section_count": n_sub,
        "prose_byte_identical": all_identical,
        "prose_byte_identity_detail": per_sub_identity,
        "prose_surface": {
            "note": (
                "Identical for both ledgers (prose is byte-identical). "
                "Sentences are a deterministic proxy for the material-assertion "
                "surface; the judge-scored E3 decomposition is not run offline."
            ),
            "sub_sections": n_sub,
            "chunks": total_chunks,
            "sentences_proxy": total_sentences,
            "words": total_words,
            "chars": total_chars,
        },
        "graph_sourced": {
            "claims": graph_n,
            "claims_deduped": len(graph_dedup),
            "claims_per_sub_section": round(graph_n / n_sub, 3) if n_sub else None,
            "status_partition": _status_partition(graph_statuses),
            "claim_summaries": [c.claim_summary for c in graph_claims],
            "records_per_100_sentences": (
                round(100 * graph_n / total_sentences, 2) if total_sentences else None
            ),
        },
        "drafter_era": {
            "claims": drafter_n,
            "claims_per_sub_section": round(drafter_n / n_sub, 3) if n_sub else None,
            "status_partition": _status_partition(drafter_statuses),
            "records_per_100_sentences": (
                round(100 * drafter_n / total_sentences, 2)
                if total_sentences
                else None
            ),
        },
        "granularity_gap": {
            "cardinality_ratio_drafter_over_graph": (
                round(ratio, 2) if ratio is not None else None
            ),
            "claims_lost_in_attribution": drafter_n - graph_n,
        },
    }


def run_e4_regression(sections_dir: Path, golden_dir: Path) -> dict[str, Any]:
    """E4's fully-deterministic golden-set comparison (drafter golden vs graph)."""
    golden = load_golden_set(golden_dir)
    current_paths = [sections_dir / f"{slug}_section.json" for slug in SECTIONS]
    report = compare_to_golden_set(golden, current_paths)

    per_section = []
    for result in report.results:
        kinds: dict[str, int] = {}
        for f in result.findings:
            kinds[f.kind] = kinds.get(f.kind, 0) + 1
        per_section.append(
            {
                "section_id": result.section_id,
                "artifact_changed": result.artifact_changed,
                "regressed": result.regressed,
                "breaking_findings": len(result.breaking_findings),
                "findings_by_kind": kinds,
            }
        )
    return {
        "note": (
            "E4 deterministic golden-set comparison (harness.regression, zero "
            "judge). The drafter-era golden is the baseline; the graph-sourced "
            "section is 'current'. Meaning-keyed ledger diff — a drafter claim "
            "with no meaning-match in the coarse graph ledger is a 'claim_removed' "
            "breaking finding, i.e. attribution granularity lost."
        ),
        "summary": report.summary,
        "sections": per_section,
    }


def build_report(repo_root: Path) -> dict[str, Any]:
    """Assemble the full measurement report. Pure — reads only, writes nothing."""
    sections_dir = repo_root / DEFAULT_SECTIONS_DIR
    golden_dir = repo_root / DEFAULT_GOLDEN_DIR

    sections = {
        slug: measure_section(slug, sections_dir, golden_dir) for slug in SECTIONS
    }

    total_graph = sum(s["graph_sourced"]["claims"] for s in sections.values())
    total_drafter = sum(s["drafter_era"]["claims"] for s in sections.values())
    total_sub = sum(s["sub_section_count"] for s in sections.values())
    total_sentences = sum(
        s["prose_surface"]["sentences_proxy"] for s in sections.values()
    )
    all_prose_identical = all(s["prose_byte_identical"] for s in sections.values())

    return {
        "record_type": "lg1_ledger_granularity_measurement",
        "ticket": "7. LG-1 — Coarse claim ledger, measured (plans/tickets_phase8_review.md)",
        "generated_by": "harness/ledger_granularity.py",
        "deterministic": True,
        "judge_layer_status": (
            "NOT RUN — E2 (per-claim faithfulness) and E3 (semantic decomposition "
            "+ coverage) require an independent, non-Claude judge endpoint. None is "
            "configured under this repo's subscription-only claude_cli transport, "
            "and the harness structurally refuses the drafter's own model for "
            "grader-generator independence (see the E3 decision-log open item). "
            "The deterministic backbone below (E4 golden-set diff + E2 status "
            "partition + E3/materiality prose surface) is sufficient for the "
            "accept-or-enrich decision because the prose is byte-identical: the "
            "assertion denominator both ledgers must attribute is constant, so the "
            "graph ledger's cardinality deficit lower-bounds the escaped-assertion gap."
        ),
        "inputs": {
            "graph_sourced_sections": DEFAULT_SECTIONS_DIR.as_posix(),
            "drafter_era_ledgers": (
                f"{DEFAULT_GOLDEN_DIR.as_posix()} "
                "(E4 golden baselines, frozen 2026-07-21)"
            ),
        },
        "totals": {
            "sections": len(SECTIONS),
            "sub_sections": total_sub,
            "prose_byte_identical_all": all_prose_identical,
            "sentences_proxy": total_sentences,
            "graph_sourced_claims": total_graph,
            "drafter_era_claims": total_drafter,
            "cardinality_ratio_drafter_over_graph": (
                round(total_drafter / total_graph, 2) if total_graph else None
            ),
            "graph_claims_per_sub_section": (
                round(total_graph / total_sub, 3) if total_sub else None
            ),
            "drafter_claims_per_sub_section": (
                round(total_drafter / total_sub, 3) if total_sub else None
            ),
        },
        "sections": sections,
        "e4_regression": run_e4_regression(sections_dir, golden_dir),
    }


def _print_summary(report: dict[str, Any]) -> None:
    print("=" * 74)
    print("LG-1  Claim-ledger granularity: graph-sourced vs drafter-era")
    print("=" * 74)
    hdr = f"{'section':16}{'subs':>5}{'drafter':>9}{'graph':>7}{'ratio':>8}{'prose==':>9}"
    print(hdr)
    print("-" * 74)
    for slug, s in report["sections"].items():
        g = s["graph_sourced"]["claims"]
        d = s["drafter_era"]["claims"]
        r = s["granularity_gap"]["cardinality_ratio_drafter_over_graph"]
        print(
            f"{slug:16}{s['sub_section_count']:>5}{d:>9}{g:>7}"
            f"{(str(r) + 'x'):>8}{('yes' if s['prose_byte_identical'] else 'NO'):>9}"
        )
    t = report["totals"]
    print("-" * 74)
    print(
        f"{'TOTAL':16}{t['sub_sections']:>5}{t['drafter_era_claims']:>9}"
        f"{t['graph_sourced_claims']:>7}"
        f"{(str(t['cardinality_ratio_drafter_over_graph']) + 'x'):>8}"
        f"{('yes' if t['prose_byte_identical_all'] else 'NO'):>9}"
    )
    print()
    print(
        f"drafter-era: {t['drafter_claims_per_sub_section']} claims/sub-section  |  "
        f"graph-sourced: {t['graph_claims_per_sub_section']} claims/sub-section"
    )
    print()
    print("E4 deterministic golden-set diff (breaking findings by section):")
    for sec in report["e4_regression"]["sections"]:
        print(
            f"  {sec['section_id']:26} breaking={sec['breaking_findings']:>4}  "
            f"{sec['findings_by_kind']}"
        )
    print()
    print("Status partition (confirmed vs inferred):")
    for slug, s in report["sections"].items():
        print(
            f"  {slug:16} drafter={s['drafter_era']['status_partition']}  "
            f"graph={s['graph_sourced']['status_partition']}"
        )
    print()
    print("Judge layer:", report["judge_layer_status"].split(".")[0] + ".")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (default: parent of harness/).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=f"Report output path (default: {DEFAULT_OUT_REL}).",
    )
    args = parser.parse_args(argv)

    # Console output carries em-dashes; force UTF-8 so a cp1252 terminal does
    # not mojibake the summary (the written JSON is UTF-8 regardless).
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

    repo_root = args.repo_root.resolve()
    out_path = args.out if args.out is not None else repo_root / DEFAULT_OUT_REL

    report = build_report(repo_root)

    # House atomic-write pattern (indent=2, ensure_ascii=False), matching the
    # sibling harness producers (regression.write_fingerprint).
    atomic_write_json(report, out_path, prefix="lg1_ledger_granularity_")

    _print_summary(report)
    print(f"\nReport written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
