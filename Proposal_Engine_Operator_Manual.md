# MSCA Proposal Engine — Operator's Manual

*A procedural guide to instantiating a project, running phases 1–8, and refining the result. Written for the operator (PI, proposal manager, methodology author) — not for the code. Keep it open; jump to the section that matches where you are.*

---

## How to use this manual

You will pass through four stages, in order, and you can re-enter the last one as often as you like:

1. **Understand the machine** — §1, once.
2. **Instantiate the project** — §3. You author a small set of fundamental documents by hand.
3. **Run the pipeline** — §4. The engine elaborates your inputs into the full proposal, gating every step.
4. **Refine** — §5. You make surgical edits in the graph and recompile — no re-drafting.

If you're mid-project and just need "which file do I touch to change X?", go straight to §6 (Quick reference). If a gate just failed, go to §7 (Troubleshooting).

---

## 1. The mental model

### Two engines, one set of documents

The system has **two** ways to produce the proposal, and they share the same `docs/` output tree:

- **The DAG scheduler** — the *generator*. It runs phases 1–8 as AI agents, each writing a slice of the proposal and passing through a **gate** before the next phase starts. It reasons, drafts, and infers. It is how a proposal is *created* from your inputs.
- **The graph compiler (`--from-graph`)** — the *deterministic press*. It reads a curated knowledge vault (an Obsidian graph) and mechanically stamps out `docs/` artifacts. It authors nothing and infers nothing — same vault in, byte-identical documents out. It is how a proposal is *edited and reproduced* once it exists.

**Rule of thumb:** the DAG *writes prose by thinking*; the graph *replays prose you already own*. Use the DAG to build; use the graph to refine.

### The tiers (where things live)

Everything flows uphill through numbered tiers:

```
Tier 1  Normative framework .......... the rulebook (HE/MSCA rules)          [fixed]
Tier 2  Call & instrument sources .... the call text, forms, work programme [you supply the call]
Tier 3  Project instantiation ........ YOUR project: concept, team, seeds    [YOU AUTHOR THIS]
Tier 4  Orchestration state .......... run outputs, gate results, logs       [engine writes]
Tier 5  Deliverables ................. Part B sections, the .docx            [engine writes]
```

Your job as operator lives almost entirely in **Tier 3**. The engine owns Tiers 4–5. Tiers 1–2 are the ground truth you point it at.

### The one-way flow (this resolves most confusion)

```
        ┌─────────────────────────────────────────────────────────────┐
        │  INSTANTIATE (you)            RUN (DAG)          REFINE (graph)│
        │                                                               │
        │  Vault + Tier-3 seeds  ──▶  phases 1–8  ──▶  Tier 3–5 output   │
        │      (author once)          (elaborate,        (gated)        │
        │                              gate each)           │           │
        │                                                   ▼           │
        │                                          lift into vault       │
        │                                                   │           │
        │                                                   ▼           │
        │                                     edit vault ──▶ --from-graph │
        │                                     (surgical)     recompile   │
        │                                                   │           │
        │                                                   ▼           │
        │                                          promote ──▶ re-gate    │
        └─────────────────────────────────────────────────────────────┘
```

It is **not** a loop between the two engines. You generate **once** with the DAG, then live in the refine cycle with the graph. You only return to the DAG if something *fundamental* changes (new concept, new consortium, new methodology) — that is a **re-instantiation**, not a refinement (see §5.4).

### The honesty principle (the guardrail that never turns off)

The engine will **never invent a fact to make a gate pass**. Every claim carries a provenance level:

| You mark a fact as… | It becomes… | Meaning |
|---|---|---|
| `source_grounded` | **Confirmed** | Backed by a real source |
| `synthesis` | **Inferred (framing)** | Your framing over confirmed facts |
| `inference` | **Inferred** | A reasoned step |
| `unconfirmed` | **Assumed** *(only if you declare it)* or **not used** | Not yet real |

If a required fact is missing and you have **not** declared it, the run stops in an **honest block** — a *correct* end state, not a failure. You unblock it by *declaring* the assumption (§2), never by pretending. This is why you flag uncertainty rather than fill it in.

---

## 2. Quick navigator — "I am at stage X"

| Your situation | Go to |
|---|---|
| Empty repo, only the call is verified | §3 (Instantiate) |
| Inputs authored, ready to generate | §4 (Run phases 1–8) |
| A phase gate failed | §7 (Troubleshooting) |
| Proposal generated, want to polish wording or tweak a WP | §5 (Refine via `--from-graph`) |
| Something fundamental changed (new partners, new methodology) | §5.4 (Re-instantiate) |
| "Which file changes X?" | §6 (Quick reference) |

---

## 3. Part I — Instantiate the project (your job)

This is the only creative authoring you do by hand. Everything downstream is elaboration of what you write here. **Author these once, deliberately, then freeze them** (see the boxed rule at the end).

### 3.0 Scaffold the authoring surface

Your knowledge lives in a per-project **vault** (an Obsidian graph). Create the empty skeleton first:

> Invoke the **`obsidian-graph`** skill (it clones the generic template `templates/obsidian_graph_vault/` into your vault and drops the folder skeleton `00…18`, `90_dashboards`, `99_governance`, plus a `graph.config.yaml`).

You now have empty vault folders and empty Tier-3 folders. Fill them in the order below. The order is not arbitrary — each document is *read by* the next, so authoring out of order leaves later documents with nothing to stand on.

### 3.1 The instantiation sequence

**① `selected_call.json`** — *the anchor* — `docs/tier3_project_instantiation/call_binding/`
Already verified in your case. It names the exact call/topic. **Read by Phase 1** (call analysis) and **Phase 4** (schedule). Everything is scoped to it. *Certainty: must be real (Confirmed).*

**② The methodology vault** — *the foundation* — vault folders `00_meta … 10_research_questions`
Author the science here: core architecture, methodological routes, state of the art, terminology, the research questions. Tag each node's `evidence_strength` honestly as you write. This is the `source_grounded` bedrock the concept and the Excellence section are lifted from. *Certainty: mark each node truthfully; `source_grounded` only where a real source backs it.*

**③ `project_brief/`** — *the seed of the whole proposal* — `docs/tier3_project_instantiation/project_brief/`
Three documents you author from the methodology:
- `concept_note.md` — the research problem, approach, and why it matters (prose).
- `project_summary.json` — the structured one-page summary.
- `strategic_positioning.md` — why this project, this fellow/host, now; fit to the call.
**Read by Phase 2** (concept refinement), which aligns your concept to the call and derives `topic_mapping.json` + `compliance_profile.json` from it. If the brief is thin, everything downstream is thin. *Certainty: your concept is Confirmed by construction (it's your intent); claims within it inherit the vault's provenance.*

**④ `source_materials/`** — *the evidence base* — `docs/tier3_project_instantiation/source_materials/`
Literature, prior results, host data. **Read by Phase 2** alongside the brief. *Certainty: real sources only.*

**⑤ `consortium/`** — *the team* — `docs/tier3_project_instantiation/consortium/`
- `partners.json` — host institution, supervisor(s), secondment/associated partners.
- `roles.json` — who does what.
**Read by Phase 3** (work packages), **Phase 4** (schedule/roles), **Phase 6** (implementation & host capacity), **Phase 7** (budget). The team shape drives the work plan and the budget. *Certainty: confirmed members are real; **not-yet-confirmed members are flagged**, not omitted and not asserted — see §2 and §3.2.*

**⑥ `architecture_inputs/` seeds** — *the skeleton the engine fleshes out* — `docs/tier3_project_instantiation/architecture_inputs/`
Author these as the vault nodes in folders `11_objectives … 17_budget` (they compile/lift into the JSON seeds):
- `objectives.json` — **read by Phase 3 & 5**
- `outcomes.json`, `impacts.json` — **read by Phase 5** (impact architecture)
- `risks.json` — **read by Phase 6** (implementation)
- `workpackage_seed.json` — **read by Phase 3**, which *refines* it
These are *seeds*, not finished sections — a few objectives, the intended WP shape, the headline risks. The DAG expands them into the full architecture. *Certainty: seeds are your design intent; the engine will not upgrade an Inferred seed into a Confirmed fact.*

**⑦ `working_assumptions.json`** — *your uncertainty ledger* — `docs/tier3_project_instantiation/`
Author this **last**, once you know what is still open. See §2 — it is important enough to have its own step. *Certainty: this file is exactly where uncertainty is allowed to live.*

### 3.2 How the inputs support the upstream procedures (at a glance)

```
selected_call ─────────────▶ Phase 1  (analyse the call → extract requirements)
project_brief ─────────────▶ Phase 2  (refine concept → topic_mapping, compliance_profile)
source_materials ──────────▶ Phase 2
objectives + wp_seed ──────▶ Phase 3  (design work packages + dependencies)
consortium ────────────────▶ Phase 3, 4, 6, 7
(phase 3 output) ──────────▶ Phase 4  (gantt + milestones)
outcomes + impacts ────────▶ Phase 5  (impact architecture)
risks + compliance ────────▶ Phase 6  (implementation architecture)
consortium + duration ─────▶ Phase 7  (budget)
everything above ──────────▶ Phase 8  (draft Part B, gate, checkpoint)
working_assumptions ───────▶ Phase 7 & 8  (turns "unknown" into honest "Assumed")
```

> **The freeze rule.** Once instantiation is complete and you start Phase 1, treat ①–⑥ as **immutable** for the duration of the run. The engine assumes they are stable ground; editing them mid-pipeline invalidates the phases already gated on them. The *only* input you keep touching is ⑦ `working_assumptions.json`, and even that you settle before the budget/drafting phases. Refinement of the *generated* proposal happens later, through the graph (§5) — not by re-editing these founding documents.

---

## 3. Part II — Flag uncertainty honestly

A real proposal always has open questions at authoring time — an unconfirmed secondment partner, a host country still being decided, a duration not yet fixed. The engine has one correct way to handle these, and one file for it.

### The one file: `working_assumptions.json`

- **You copy** `working_assumptions.example.json` → `working_assumptions.json` and edit it. The engine **reads it and never writes it** — it is yours.
- **Each declaration** turns an otherwise-Unresolved fact into a conscious **Assumed** (never Confirmed). Every Assumed claim in the final proposal must trace back to a declaration here (the W1 rule enforces this).
- **Shape** of a declaration:

```json
{
  "key": "host_country",
  "value": "BE",
  "declared_by": "operator@org.eu",
  "declared_on": "2026-07-13T10:00:00Z",
  "rationale": "Host located in Belgium; sets the unit-cost coefficient and the Assumed host identity.",
  "checklist_ref": "HOST"
}
```

Common declarations: `HOST` (host country/institution), `DURATION` (fellowship months), and any unconfirmed partner. One host declaration can resolve *both* the Phase-7 budget coefficient *and* the Phase-8 Assumed host claims at once.

### The other place: `evidence_strength` on vault nodes

As you author vault nodes, tag each with its true provenance (`source_grounded` / `synthesis` / `inference` / `unconfirmed`). The compiler *computes* the published status from this tag — it never trusts prose. An `unconfirmed` node is simply not lifted as a fact. This is flagging at the source.

### Unconfirmed partners specifically

Use the `Unconfirmed Partner Placeholders` node in the vault's `08_partners/` for members still under negotiation, and add a matching `working_assumptions.json` declaration. They then appear as **Assumed** — visible, honest, and swap-in-ready when confirmed.

### What happens if you *don't* flag

The run reaches an **honest block (mode α)** and stops. This is **not a bug** — it is the engine refusing to fabricate. Read the block, decide whether the fact is real (→ put it in a source and mark `source_grounded`) or provisional (→ declare it in `working_assumptions.json`), and re-run.

---

## 4. Part III — Run the pipeline (phases 1–8)

### The command

```bash
python -m runner --run-id <fresh-uuid>
```

- **Always use a fresh `--run-id`** for a new project or a from-scratch regeneration. Never reuse a prior run's id.
- Add `--verbose` to watch the scheduler on stderr.
- To execute a single phase for inspection: `--phase 3` (runs only that phase; nothing downstream).

The scheduler walks the phases in order. **Each phase ends at a gate.** If the gate passes, the next phase starts; if it fails, the run stops at that node with a reason. You fix the cause and re-run.

### What each phase does, and what its gate protects

| # | Phase | It produces | Its gate checks (plain terms) |
|---|---|---|---|
| 1 | **Call analysis** | Extracted call requirements (expected outcomes/impacts, scope, eligibility, evaluation weights) | The call was parsed completely and correctly |
| 2 | **Concept refinement** | `topic_mapping`, `compliance_profile`, refined concept | Your concept aligns to the call and is compliant |
| 3 | **Work-package design** | Work packages + dependencies | WPs are well-formed, dependencies are acyclic, traceable to objectives |
| 4 | **Gantt & milestones** | `milestones_seed`, schedule | Timeline is consistent with WPs and duration |
| 5 | **Impact architecture** | Impact pathways, DEC (dissemination/exploitation/comms) | Impact traces to outcomes; pathways are complete |
| 6 | **Implementation architecture** | Governance, risk register | Risks, governance, host capacity are sound and compliant |
| 7 | **Budget** | Budget request | Budget derives correctly from duration/host/WPs (unit-cost rules) |
| 8 | **Drafting & review** | **Part B** (Excellence, Impact, Implementation) + checkpoint | Sections complete, every claim traceable, canonical terms preserved, no over-stated status (`gate_10a–10d`, `gate_11`), then the run checkpoint (`gate_12`) |

### What "done" looks like

- All eight phase gates green.
- Tier-5 holds the three Part B section JSONs (and the `.docx` if you export it).
- A **checkpoint** (`phase8_checkpoint.json`) is published — the durable "this run passed" record. It is **write-once**: to regenerate from scratch later, archive it first (see §7).

### The golden rule of a from-scratch run

**Run fresh, do not bootstrap.** A from-scratch project must not inherit a previous run's gate evidence. If you (or a script) try to, the freshness check compares the *content* of your new inputs against the old recorded fingerprints, finds them different, and fail-closes — which is the system correctly stopping you from building new deliverables on stale foundations. So: new run-id, no inherited upstream gates, let every phase re-validate.

---

## 5. Part IV — Refine after the run (`--from-graph`)

Once phases 1–8 have produced a gated proposal, you switch modes. Refinement no longer means "re-run the AI and hope it keeps everything else" — it means **edit the vault and recompile deterministically**.

### 5.0 One-time setup: seed the vault from the run

If you generated with the DAG, first lift the finished output into the vault (the authoring surface). From then on the vault is your source of truth for Tier-3 architecture and Part B, and you edit *there*.

### 5.1 The refine cycle (memorise this loop)

```
edit vault node  →  compile  →  review diff  →  promote  →  re-gate
```

```bash
# 1. edit the relevant vault node(s) in Obsidian  (see 5.2 for what you can change)
# 2. compile — deterministic, writes only to a staging area, touches nothing live:
python -m runner --run-id <id> --from-graph MSCA/graph.config.yaml
# 3. review the diff it produced (diff_report.json / part_b_report.json) — confirm only what you intended changed
# 4. promote — the deliberate, backed-up, reversible cutover to docs/:
python tools/promote_graph_staging.py --config MSCA/graph.config.yaml --apply
# 5. re-gate — run the scheduler with drafting skipped so the gates re-check your edit:
python -m runner --run-id <fresh-id> --preseed-phase8-sections
```

Step 5 is what preserves every guardrail: it **skips only the expensive drafting**, but still runs the audit skills and the **full Phase-8 gate chain** on your edited content. If your edit introduced an unsupported claim, over-stated a status, or dropped a required term, the same gate that guards an AI draft fails here. Compilation is deterministic; validation is unchanged.

### 5.2 What you can refine this way

| Edit | Where (vault) | Effect |
|---|---|---|
| Tighten / rewrite a paragraph | `19_proposal_sections/` node body | New Part B prose, re-gated |
| Re-tag a claim's certainty | node `evidence_strength` | Published status recomputed (can't fake Confirmed) |
| Add / fix a citation | node `source_refs` | Traceability updated |
| Adjust an objective / outcome / impact | `11–13` nodes | Architecture input regenerated |
| Add or reshape a work package | `14_work_packages` | WP seed regenerated (re-run affected phases if structural) |
| Revise a risk / timeline / budget line | `16 / 15 / 17` nodes | Corresponding architecture input regenerated |

### 5.3 What `--from-graph` will *not* touch

The graph owns **Tier-3 `architecture_inputs` + Part B only**. It does **not** regenerate `consortium/`, `call_binding/` (beyond `selected_call`), or `project_brief/`. To change those, update the input (§3) and re-run the affected phases — they are not graph-refinable.

### 5.4 When refinement is not enough — re-instantiate

If the change is *fundamental* — new consortium members, a new methodology, a reframed concept — editing vault nodes by hand would mean rewriting most of them, which defeats the point. Instead, treat it as a **new instantiation**:

1. Update the founding **inputs**: `consortium/` (new members), the methodology vault, `working_assumptions.json` (declare anything not yet confirmed), and review `compliance_profile`. Keep `selected_call` (same call).
2. **Run the DAG fresh** (new run-id, no bootstrap) — phases 1–8 re-derive Tier-3 architecture, the brief-driven sections, and Part B from the new inputs, gating throughout.
3. **Re-seed the vault** from the new output, and resume the §5.1 refine cycle.

The DAG is the tool for generating fresh content from changed inputs; the graph is the tool for polishing content that already exists. Match the tool to the size of the change.

---

## 6. Quick reference — "which file changes X?"

| I want to change… | Touch… | Then… |
|---|---|---|
| The target call | `call_binding/selected_call.json` | full re-run (§5.4) |
| The research concept | `project_brief/*` + methodology vault | full re-run (§5.4) |
| A consortium member | `consortium/partners.json` + `roles.json` | re-run phases 3–8 |
| An open assumption (host, duration, unconfirmed partner) | `working_assumptions.json` | re-run affected phases |
| An objective / outcome / impact / WP / risk / budget line | the matching vault node (`11–17`) | `--from-graph` cycle (§5.1) |
| Wording of a Part B section | vault `19_proposal_sections/` node | `--from-graph` cycle (§5.1) |
| A claim's certainty or citation | node `evidence_strength` / `source_refs` | `--from-graph` cycle (§5.1) |

**Commands cheat-sheet**

```bash
python -m runner --run-id <uuid>                         # full pipeline, phases 1–8
python -m runner --run-id <uuid> --phase 3               # one phase, for inspection
python -m runner --run-id <uuid> --from-graph <config>   # compile vault → staging (no gates, non-destructive)
python tools/promote_graph_staging.py --config <config> --apply   # promote staging → docs/ (backed up, reversible)
python -m runner --run-id <uuid> --preseed-phase8-sections        # re-gate graph-sourced sections (drafting skipped)
```

---

## 7. Troubleshooting

**A phase gate failed.** Read the reason at the blocked node. It is telling you the *content* is wrong (a missing trace, an over-stated status, an inconsistency), not that the machine broke. Fix the cause in the responsible input/vault node and re-run. Gates are the product working, not failing.

**The run stopped in an "honest block."** A required fact is unresolved and undeclared. Decide: real → add a source and mark `source_grounded`; provisional → declare it in `working_assumptions.json`. Re-run. (§2)

**"Checkpoint already exists."** The prior run's write-once `phase8_checkpoint.json` is still in place. Archive it (move it aside with a dated name and a one-line note in the decision log), then re-run.

**Freshness rejected my inputs as "stale."** You tried to reuse/inherit a prior run's evidence after changing inputs. Correct behaviour. Start a fresh run-id with no inherited gates (§4, §5.4).

**`--from-graph` "changed" the whole repo / weird line-ending diff.** Ensure line endings are normalised before compiling (a whole-tree CRLF flip is cosmetic but noisy). Compile is non-destructive regardless — nothing lands in `docs/` until you `--apply` the promote.

---

## 8. Appendix — map & glossary

**Tier / folder map**

```
docs/tier3_project_instantiation/
  call_binding/      selected_call*, topic_mapping, compliance_profile, confirmation_checklist
  consortium/        partners.json, roles.json
  project_brief/     concept_note.md, project_summary.json, strategic_positioning.md
  source_materials/  (your literature/evidence)
  architecture_inputs/  objectives, outcomes, impacts, workpackage_seed, milestones_seed, risks, budget
  working_assumptions.json          ← your uncertainty ledger

MSCA/methodology_graph/  (the vault)
  00–10  methodology (you author)      11–17 architecture (compiles to Tier-3)
  18     gate-state mirror (auto)      19    proposal sections / Part B
  90 dashboards   99 governance

* selected_call is human-verified; topic_mapping/compliance_profile are engine-written in Phase 2.
```

**Glossary**

- **DAG scheduler** — the AI pipeline that generates and gates the proposal, phases 1–8.
- **Graph compiler (`--from-graph`)** — deterministic vault→docs press; no AI, no gates.
- **Gate** — an automatic pass/fail check at the end of each phase; guards completeness, traceability, honest status.
- **Promote** — the explicit, backed-up step that makes compiled staging the live `docs/`.
- **Checkpoint** — the durable, write-once "this run passed phase 8" record.
- **Honest block (mode α)** — the correct terminal state when a required fact is unresolved and undeclared.
- **`evidence_strength`** — a vault node's provenance tag; determines the published claim status.
- **`working_assumptions.json`** — operator-owned declarations that turn open facts into honest *Assumed* claims.
- **Re-instantiation** — a fresh from-scratch generation after a fundamental change (vs. a graph refinement).

---

*Two sentences to keep in your head: **The DAG builds by thinking; the graph replays what you own.** **Never fabricate a fact to pass a gate — flag it, and let the block be honest.***
