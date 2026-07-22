# WAVE 6 / TICKET 13 — STATE RECORD & HANDOFF

**Date:** 2026-07-14 · **Branch:** `msca-pf-milestone1`
**Purpose:** Terminate the current session. This is the authoritative state. A new session resumes from here, **after the operator has run Phases 1–6.**

---

## 0. RULES FOR THE NEXT SESSION — READ FIRST

1. **You NEVER invoke `python -m runner` or `scripts/run_msca_pf_e2e.py`. Not once. Not to "just verify."**
   The **operator** executes every phase from their own terminal. You do not chain phases, you do not
   run background shells watching a run. A previous session burned ~250k tokens doing exactly that.
2. **Your role:** (a) make edits the operator explicitly authorises, (b) diagnose failures the operator
   pastes to you, (c) stop and hand back. After each authorised edit, hand back and wait.
3. **Never add a fifth validation status.** The vocabulary is closed at the four §12.2 categories
   (Confirmed / Inferred / Assumed / Unresolved). `synthetic: true` is a *provenance flag*, never a
   status. A fifth status bypasses BOTH honesty gates (`no_unresolved_material_claims` fails only on
   `unresolved`; W1 governs only `assumed`). See `decision_log/status-vocabulary-correction_2026-07-13.json`.
4. **The engine never invents.** The operator may override (§3, logged); the engine may not (§13.3).
5. **One writer per file.** Double-write collisions have already silently eaten edits in this repo.

---

## 1. GIT STATE

| | |
|---|---|
| Branch | `msca-pf-milestone1` |
| `381352f` | Ticket-13 build + α honest-block evidence + SYN-SPINE-01 synthetic spine |
| `576f9ff` | α evidence rescue (phase-2 gate result, summary, run log) |
| tag `honest-tier3-unresolved-spine` → `1791520` | Honest Tier 3, spine Unresolved (pre-synthetic) |
| tag `alpha-honest-block` → `381352f` | α evidence commit |

---

## 2. DONE — DO NOT REDO

**α (the milestone's headline artifact) — captured and preserved.**
The live governed DAG honest-blocked at **Phase 2**: the semantic scope gate refused to proceed while
the researcher/host/supervisor spine was Unresolved, enumerating **SCL-01..04** (geographic placement,
career development plan, joint application, 6/8 expected outcomes Assumed). This satisfies ticket 13's
α criterion and D14's honest-block terminal state.
Evidence: `docs/tier4_orchestration_state/alpha_honest_block/` (gate result, concept summary, run artifacts).

**SYN-SPINE-01 — synthetic spine applied across 10 Tier 3 files** under an explicit CLAUDE.md §3
operator override of §13.3, **scoped to the spine only**, logged per §9.4 in
`decision_log/synthetic-spine-demo-override_2026-07-13.json` (canonical definition — read it; do not
invent variants).

- FELLOW = Dr. Mariya Petrova [SYNTHETIC], Plovdiv University (BG)
- HOST = Eötvös Loránd University (ELTE), Budapest — **HU** (drives the unit-cost country coefficient)
- SUPERVISOR = Prof. Dr. Gábor Nagy [SYNTHETIC], ELTE
- VALIDATION_PARTNER = AgroVIR Kft. [SYNTHETIC ARRANGEMENT]
- FELLOWSHIP_TYPE = European Fellowship, 24 months (**derived**, not invented: BG → HU is intra-EU)

**Ticket-13 build** — decomposed drafting, deterministic assembler, assumption-applier, unit-cost budget
deriver, W1 predicate, docx exporter. Committed and test-green.

**Transport root cause — FOUND AND FIXED.** `.env` defaults to `bedrock_converse` (IAM). Only
`ORCHESTRATOR_TRANSPORT_PRESET=CLAUDE_REFERENCE` resolves to `claude_cli` (local, Max-auth).
**This was the previous session's hour-long Phase-1 stall.** Every runner invocation must carry the preset.

**docx synthetic marker** — auto-detects the SYN-SPINE-01 override record and stamps
`SYNTHETIC DEMO — NOT FOR SUBMISSION`. Absent on real runs. 12 docx tests green.

**Driver docstring corrected** — it wrongly assumed α blocks at `gate_09` (Phase 7); it blocks at Phase 2.

---

## 3. CURRENT LIVE STATE — WHERE THE RUN STOPPED

Run-id in progress: **`msca-pf-syn-01`**

- **Phase 1 — RELEASED.** Bootstraps clean (`selected_call.json` was never modified, so it stayed fresh).
- **Phase 2 — BLOCKED** (runner exit code 1) on `no_unresolved_scope_conflicts`.

**SCL-01..04 (the spine conflicts) are RESOLVED** — SYN-SPINE-01 worked as intended.
**Three NEW blockers appeared:**

| # | Blocker | Nature |
|---|---|---|
| 1 | `strategic_positioning.md` still says the spine elements "remain Unresolved", contradicting `roles.json` (Confirmed) | **Incomplete SYN-SPINE-01 propagation.** Inside the existing override. |
| 2 | Career Development Plan timing: concept says "month 3"; MSCA-PF **SR-05 (mandatory)** requires the CDP as a deliverable **at the start of the action** | **Real call-compliance gap.** The correction is objectively right. |
| 3 | Missing mandatory training dimensions — digital skills, knowledge valorisation, innovation/entrepreneurship, research integrity — **SR-04 (mandatory)** | **Real call-compliance gap.** |

**What this means:** the gate is working. Giving the project a fellow and a host did not make it
MSCA-compliant. The vault project is a *remote-sensing methodology*, not an MSCA-PF-shaped project.
**SYN-SPINE-01 (identity) was necessary but NOT sufficient.**

---

## 4. THE OPEN DECISION — OPERATOR'S, NOT THE AGENT'S

The logged §3 override covers **the spine only** ("does not extend to any other data").

- **Gap 1** is inside the existing override — just finish propagating SYN-SPINE-01. Safe to authorise.
- **Gaps 2 and 3** require adapting **concept content**, which is *beyond* the logged scope. They are
  **not fact-fabrication** (you'd be making a synthetic project comply with a real call's mandatory
  requirements), but they still need the **override extended and logged**, or the record stops matching
  what is on disk — and that record is the only thing separating a sanctioned demonstration from the
  silent fabrication this engine exists to prevent.

**Whack-a-mole watch:** if Phase 2 keeps surfacing new scope gaps after each pass, that is the gate
telling you the vault project genuinely is not MSCA-PF-shaped — and at some point *that finding is the
result*, not an obstacle.

---

## 5. WHAT REMAINS TO CLOSE TICKET 13

1. Resolve the Phase-2 blockers (per §4 above).
2. **Operator runs Phases 2–6** from the terminal.
3. **Operator runs the β tail:** `python scripts/run_msca_pf_e2e.py beta --run-id msca-pf-syn-01`
   → Phase 7 → **builds the Phase-8 canonical reference pack** (easy to miss; the canonical-preservation
   gates fail without it) → Phase 8 (live decomposed drafting) → `.docx` → snapshot.
4. **CI:** `pytest tests/runner/test_e2e_msca_pf_run.py tests/runner/test_assumption_applier.py tests/runner/test_unit_cost_budget.py tests/runner/test_w1_assumed_claims.py`
   (both byte-equal invariants + W1 both ways).
5. **Independent traceability re-verify** — and record honestly that on synthetic data it verifies
   **mechanism, not truth**: claims trace to Tier 3 because the fabricated facts *are* in Tier 3.
6. **Close ticket 13 with BOTH outcomes:**
   - **α (tagged):** live governed DAG → honest block at Phase 2 on the unresolved spine (SCL-01..04).
   - **Option 0 (SYN-SPINE-01):** live governed DAG → full green B1 + marked `.docx`.

---

## 6. OPERATOR RUN COMMANDS (PowerShell)

```powershell
$env:ORCHESTRATOR_TRANSPORT_PRESET = "CLAUDE_REFERENCE"   # MANDATORY - else it hits Bedrock and stalls
$RID = "msca-pf-syn-01"                                    # ONE run-id for ALL phases - not optional

python -m runner --run-id $RID --phase 2 --verbose
python -m runner --run-id $RID --phase 3 --verbose
python -m runner --run-id $RID --phase 4 --verbose
python -m runner --run-id $RID --phase 5 --verbose
python -m runner --run-id $RID --phase 6 --verbose

python scripts/run_msca_pf_e2e.py beta --run-id $RID       # Phase 7 -> canonical pack -> Phase 8 -> docx
```

**Why ONE run-id:** `gate_10a` checks `gate_pass_recorded(gate_09, run_id)` — the budget gate must have
passed *for the current run*. Fresh run-ids per phase will fail Phase 8.

**Do NOT modify Tier 3 between phases** — a changed mtime restales gates you have already passed.

---

## 7. FINDINGS TO CARRY TO MILESTONE 2

1. **The β declaration substrate reaches only Phase 7 (budget) and Phase 8 (applier + W1).** No Phase 2–6
   skill or semantic predicate reads `working_assumptions.json`, so declaring the spine cannot unblock the
   Phase-2 scope gate. → **M2 ticket: extend the substrate to Phases 2–6, with W1-equivalent provenance
   guards on each.** SYN-SPINE-01 is the demo shortcut; that ticket is the honest fix.
2. **An MSCA-PF concept is spine-dependent at the semantic level** — you cannot scope-align a fellowship
   without knowing the fellow, host and supervisor. The gates discovered this; nobody predicted it.
3. **Identity is not sufficient for scope compliance.** Even with the spine resolved, the concept must
   independently satisfy the call's mandatory scope requirements (SR-04 training dimensions, SR-05 CDP
   timing). A vault project adapted from another domain will not be call-compliant by default.
