# Part B Final Drafting Strategy — draft → revision-actions handout → submission form

Date: 2026-09-03. Branch: `fieldwise-run-03`. Status: PROPOSED (operator approval pending).

This plan implements the "condense from the run-03 export" path that
`plans/tickets_proposal_issues_2026-09.md` (RE-SCOPED 2026-09-02) delegates to the
condensation pass, and closes the 10 unresolved revision actions of
`docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json`
(run `7860a89a`, gate_12 green 2026-09-03). It follows the round-2 open-decisions
conventions of `plans/reports/FIELDWISE_open_decisions_round2_2026-08-31.md` and the
manual-edit flags of `plans/reports/fieldwise-run-03_flags.md`.

**Sequence (fixed by design):** unbounded annotated draft FIRST → revision-actions
handout SECOND (so every question cites an exact section/¶/sentence anchor in the draft)
→ answer integration → page-limited submission form LAST. The submission form is not
started until every revision action is either resolved or parked in the handout with its
fallback applied.

---

## 1. Binding inputs and constraints

| Constraint | Source | Value |
|---|---|---|
| Template | `docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA PF).rtf` | v5.0 (27 March 2026) — structure must be followed |
| Part B-1 page limit | `section_schema_registry.json` (`part_b_page_limit_hard`) | **10 pages, hard** — sections 1+2+3 together, *including all tables, figures, references*; excess pages hidden by the submission system |
| Part B-1 sections | same registry | 1.1–1.4 (Excellence, 50%), 2.1–2.3 (Impact, 30%), 3.1–3.2 (Implementation, 20%) |
| Part B-2 | same registry | sections 4–8 (CV, participating-organisation capacity, ethics, security, Green Charter) — no page limit |
| Content source | run-03 Tier 4/5 outputs | `final_export.json` / `part_b_json_bundle.json` (run `7860a89a`), the three `proposal_sections/*.json`, plus Tier 3 for any fact verification |
| Structural reference | `final_exports/FIELDWISE_Part_B1_manual-condensed_2026-08-30.docx` | run-02 master: reference for **prose density, tables, citation style, per-section length calibration ONLY** |
| Schedule | tickets file ground rule 5 + run-03 instantiation record | freeze **2026-09-06**, upload by 2026-09-08, deadline 2026-09-09 |

**Run-02 reference caveat (binding).** The 2026-08-30 docx predates the supervisor
change; its supervisor/host-arrangement content is superseded by the run-03 spine
(all-Assumed, per the run-03 instantiation record). It may be mined for structure, table
layouts, citation format and how 10 pages were apportioned — never for supervisor,
co-supervision, or hosting facts. Every fact in the new form comes from run-03 Tier 3–5
state.

**Constitutional rules in force.** No new facts outside Tier 3 (§13.3) — anything a
researcher answer adds becomes a Tier 3 / `working_assumptions.json` edit *before* it is
asserted in the form (paired-edit rule, tickets file ground rule 2; never declare a
call-binding-Confirmed fact in working_assumptions). Gaps that survive to the freeze are
flagged in the deliverable, not papered over (§11.5, §13.8). Claude never dispatches
runner phases; the operator runs any pipeline command from the CLI.

---

## 2. Revision-action triage

Classification decides what goes into the draft directly and what goes into the handout.
"Draft-resolvable" = closable from existing Tier 3/4 state by rewording or tabulating —
no new fact needed. "Needs input" = requires a decision or a fact not in Tier 3.

| Action | Sev. | Target | Class | Owner of the answer |
|---|---|---|---|---|
| A-1 month-3 freeze vs M14 D1.1/D1.2 sequencing | major | 1.1 + 1.2 | **needs input** — choose: provisional pre-freeze protocol narrative vs shifting due months (touches work plan) | supervisor + fellow |
| A-2 beyond-SotA: name the new citable knowledge | major | 1.1 | **needs input** — scientific claim only the fellow/supervisor can commit to | fellow + supervisor |
| A-3 ELTE training capacity secured + host-side continuity safeguard | major | 1.3 | **needs input** — Tier 3 lacks the letters; safeguard is an institutional commitment | operator + host |
| A-4 method-anchored expected-effect ranges | major | 2.3 | **needs input** — 2.3 deliberately declined project-specific targets (fragile sub-section; prior operator decision) | fellow + supervisor |
| A-5 month-by-month effort loading at WP1/WP3/WP4 peak + in-kind offload framing | major | 3.1 | **split**: loading table is draft-resolvable from `phase4_gantt_milestones/gantt.json` + wp_structure; the offload framing needs partner confirmation | draft + partners confirm |
| A-6 WP3 lead reassignment to fellow/beneficiary | major | 3.1 | **needs input** — changes a recorded WP-lead fact (Tier 3 roles / Tier 4 wp_structure); prose + paired Tier 3 edit after decision | operator + fellow |
| A-8 concrete post-fellowship trajectories + named career KPI | minor | 2.1 | **needs input** (KPI may already exist in Tier 4 KPI set — verify first; if present, draft-resolvable by naming it) | fellow |
| A-9 measurable dissemination/uptake indicators | minor | 2.2 | **needs input** — proposable from existing channels, needs owner confirmation of numbers | fellow + operator |
| A-10 quantify near-term reachable segment | minor | 2.3 | **needs input** — a number with a citable source; cannot be invented (§13.2/§13.3) | fellow (source), operator |
| A-11 WP2 numbering-gap note | minor | 3.1 | **draft-resolvable** — one-line note; OD-1 merge already recorded in Tier 3/4 | — (verify only) |

A-7 and A-12 are resolved (see `revision_log` L-7/L-12); the draft must *preserve* the
1.4 artefact framing and 3.2 capacity/PIC content that resolved them.

---

## 3. Stage 1 — Unbounded annotated draft (target: 2026-09-03/04)

Produces `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B_draft_run-03_2026-09-04_annotated.docx`.

1. **Regenerate the base draft from today's export.** The committed
   `part_b_draft.docx` is 2026-08-30 (stale). Re-render from the current
   `final_export.json` via `runner/docx_exporter.py::export_part_b_docx` (deterministic
   rendering, not a phase dispatch), then copy to the dated filename above; never leave
   the output only in the overwritable `part_b_draft.docx` slot.
2. **Apply the ¶-anchor scheme.** Number every paragraph per sub-section using the
   established draft ¶-numbering scheme (`1.1-¶3` style; sentences `s1, s2, …` within a
   ¶). Anchors are stable ids for the handout and for the condensation map — they are
   stripped only in the final form.
3. **Resolve the draft-resolvable items in place.** A-11 note; A-5 effort-loading table
   derived strictly from gantt.json/wp_structure (flag it "derived from Tier 4, no new
   fact"); A-8 KPI naming if the KPI exists in the Tier 4 KPI set.
4. **Annotate every remaining action at its exact location.** python-docx 1.2.0 supports
   native Word comments: at each targeted ¶/sentence, add a highlighted run
   `[A-x]` plus a Word comment carrying the action description, the question for the
   researcher, and the proposed fallback. One comment per anchor; an action touching two
   sub-sections (A-1) gets an anchor in each.
5. **Implementation:** a small deterministic script `tools/annotate_part_b_draft.py`
   (reads the section JSONs, `drafting_review_status.json`, and a hand-authored
   `plans/reports/partb_draft_anchor_map_2026-09.json` mapping action_id → anchor list;
   writes the annotated docx). Keeping the anchor map as data makes the annotation
   re-runnable when the draft regenerates.
6. **Verification:** all 10 unresolved action_ids appear ≥1 time; A-7/A-12 content
   spot-checks pass; no supervisor/host fact contradicts the run-03 Tier 3 spine.

## 4. Stage 2 — Revision-actions handout, OD round 3 (immediately after Stage 1)

Produces `plans/reports/FIELDWISE_open_decisions_round3_2026-09-04.md` + a docx export
for circulation alongside the annotated draft.

- **Format mirrors round 2:** per item — owner, needed-by date, the reviewer's point,
  the underlying question (not a yes/no), a draft answer marked
  **Assumed-pending-confirmation** grounded only in existing Tier 3/Pack content, and an
  explicit **fallback** (always the honest currently-confirmed position, never a
  strengthened claim).
- **One entry per needs-input action** (A-1, A-2, A-3, A-4, A-5-confirm, A-6, A-8*,
  A-9, A-10), each citing its draft anchors (`section 1.1, ¶3, s2 — see comment [A-2]`)
  so answers can be applied unambiguously. *A-8 only if the KPI turned out not to exist
  in Tier 4.
- Draft-resolved items (A-11, A-5 table) are listed in a closing "resolved in draft —
  verify" table so reviewers can veto rather than author.
- **Answers needed by 2026-09-05 EOD** (hard, given the 09-06 freeze). Unanswered items
  take their stated fallback and are logged as such.

## 5. Stage 3 — Answer integration (2026-09-05, rolling as answers arrive)

Every answer lands in three places, in order. First the paired edit: the Tier 3
artifact is updated before the draft prose — or a keyed `working_assumptions.json`
declaration where the fact remains Assumed. Second, the resolution is recorded in a
§9.4 decision-log record (one consolidated `od-round3-resolutions_2026-09-0X.json`).
Third, the corresponding Word comment in the draft is marked resolved.
`drafting_review_status.json` is a run artifact and is **not** hand-edited — resolution
lives in the decision log and the handout's answer column. Whether to re-run n08e/f to
regenerate a green review status is an operator option, out of scope here.

Respect the id-stability rule for any Tier 3 edit (A-6 especially: WP3 lead changes in
`roles.json`/`workpackage_seed.json` reuse existing ids).

## 6. Stage 4 — Submission form (2026-09-05/06, freeze 09-06)

Produces `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_manual-condensed_2026-09-06.docx`
(dated copy; the 2026-08-30 file is never edited in place — tickets file ground rule 1).

1. **Skeleton from the official template:** headings/order exactly per the RTF v5.0
   (1.1–1.4, 2.1–2.3, 3.1–3.2; B-2 sections 4–8 as a separate document per the template's
   Part split).
2. **Condense the resolved draft into the skeleton,** calibrating per-section length
   against the run-02 master's apportionment of the 10 pages; keep its citation style
   and table treatments; carry over zero superseded supervisor/host content.
3. **Apply the run-03 manual-edit flags** (`fieldwise-run-03_flags.md`) and the still
   -pending docx-halves of tickets T1–T8 that the condensation subsumes.
4. **Pre-freeze checklist (all must pass):**
   - B-1 ≤ 10 pages with tables/figures/references included (print-layout check);
   - every template sub-section present, none empty;
   - all 10 revision actions resolved-or-fallback, each traceable to the decision log;
   - anchor/comment markup fully stripped;
   - §11.4 sweep: no sentence contradicts run-03 Tier 3 (spot-check the A-6 WP-lead,
     A-3 supervision, and effort-table numbers against Tier 3/4);
   - unresolved-at-freeze gaps flagged in-text per §13.8, and mirrored into the T11
     submission record.
5. Freeze 2026-09-06; T10/T11 of the tickets file govern from there (upload 09-08).

---

## 7. Out of scope / prohibitions

- No runner phase dispatch by Claude (operator CLI only); no Tier 1/2 source edits.
- No budget figures beyond the gate-validated §8.1 derivation (€220,723.50 total).
- No strengthening of claims via fallback answers; fallbacks are the honest floor.
- `FIELDWISE_Part_B1_manual-condensed_2026-08-30.docx` and `part_b_draft.docx`
  (2026-08-30) are preserved as snapshots.
