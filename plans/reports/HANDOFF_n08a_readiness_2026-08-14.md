# Handoff — n08a (Excellence drafting) readiness

**For:** the next session that will run `n08a_excellence_drafting` to green.
**Branch:** `fieldwise-run-01`, last commit `350c4f3`. Working tree has uncommitted Tier 3 / Tier 4 / runner changes (below).
**Status:** all blockers diagnosed and fixed **except one node re-run**. n08a has never yet been run under the current fixes.

**Operator constraint that shapes everything here:** roughly half the maximum subscription session
quota is already spent. Two n08a attempts have failed. **Do not spend a run to find something out
that can be established for free.** The applier, the assemblers, the canonical-pack deriver and
every `gate_10a` predicate are deterministic and Claude-free. Almost all of this is checkable
without quota; sections 5 and 6 tell you how.

---

## 0. TL;DR

1. Re-run **n07** (mandatory — it is stale, see §2).
2. Re-run **n08a with a NEW run-id** (mandatory — the existing drafts are dead, see §3).
3. Do **not** re-run n01–n06. They are fresh and passing.

Everything else is done.

---

## 1. What was wrong, and what fixed it

Three distinct defects, all now closed. Understanding them matters because the second and third
only take effect on a **fresh draft**.

### 1.1 The canonical pack was empty (fixed, verified)

`runner/phase8_canonical_pack.py` looked for `id` / `measurable_target`, while the FIELDWISE
hand-lift wrote `objective_id` / `measurable_output`. Every objective was silently dropped, the
required-non-empty backstop fired, and the node died with `AGENT_EXECUTION_ERROR`.

Worse and quieter: `outcomes` (`outcome_id` / `statement`) also extracted **0 of 6**, and `outcomes`
was *not* in `_REQUIRED_NONEMPTY`, so it failed silently. The preservation predicates early-return on
empty arrays, so they would have **vacuously passed** over unchecked prose.

Fixed by source-key aliasing (a pure rename, no inference) plus adding `outcomes` to the backstop.
Now extracts 6/6 objectives and 6/6 outcomes. `involved_partners` is deliberately **not** mapped to
`responsible_partner` — the source does not distinguish responsible from contributing, so mapping it
either way would be inference about a project fact (§13.3).

### 1.2 The applier could never fire (fixed, verified)

`runner/assumption_applier.py` resolved a claim to a declaration by **key only**. The drafter named
the claim `MOBILITY_ELIGIBILITY` — the declaration's `checklist_ref`, not its key
`mobility_eligibility`. `WorkingAssumptions.by_checklist_ref()` existed for exactly this bridge; the
applier never called it. Result: the operator had declared the fact and the gate still blocked.

Fixed with a two-step resolver (key first, then `checklist_ref` **only when unambiguous** — a ref
shared by several declarations resolves to nothing, because choosing would be a judgment this
component may not make). On flip it now also normalizes `claim_id` to the declaration key.

**That normalization is not cosmetic.** W1 (`assumed_claims_are_operator_declared`) matches by key,
so a bridged flip carrying the ref would have traded a `p06` failure for a `p11` failure. Setting
the key is a no-op on the exact-key path, so both paths converge and **W1 needed no change**.

### 1.3 The honesty layer was inert (fixed — takes effect on a fresh draft only)

The live drafting prompt in `runner/decomposed_drafting.py` offered only
`confirmed | inferred | unresolved` and said *"never emit status 'assumed' yourself"*, but never said
what to do with a fact whose only source is a declaration. The drafter had no correct option and
chose `inferred`. Consequence:

- Three operator-declared facts were presented to the evaluator as *derived from confirmed evidence*.
- `g09a_p11` (W1) passed **vacuously** — zero `assumed` claims to audit.
- The applier had nothing to flip.

Three fixes:

- **Drafting instruction:** a declaration-backed fact gets `unresolved` with `claim_id` set to the
  declaration's `key` verbatim, with `inferred` explicitly forbidden and the reason given.
- **Drafting instruction:** the ledger records only claims the prose actually makes — no entries for
  facts deliberately not asserted, and none about repository/input/tooling state. This kills the
  class that produced both `C-CANONICAL-PACK-MISMATCH` and `CC_ELTE_TRACK_RECORD_DEFERRED`.
- **New predicate W2** `declared_facts_are_not_inferred` (`g09a_p12` / `g09b_p13` / `g09c_p12`):
  fails any claim marked `inferred` that cites `working_assumptions.json`. Deliberately narrow — it
  judges only `inferred` and never infers that a claim *ought* to have cited a declaration.

**Wiring warning for anyone adding a predicate here.** A predicate needs *five* registrations, and
the fifth is easy to miss: the function, the `runner/predicates/__init__` export, the
`gate_rules_library.yaml` entry, the manifest `predicate_refs`, **and**
`runner/gate_evaluator.PREDICATE_REGISTRY`. Library + manifest alone leaves it unresolvable at gate
time. (Predicates of `type: semantic` are the exception — they dispatch via
`dispatch_semantic_predicate` and are correctly absent from that registry.)

---

## 2. n07 is stale — this is the one mandatory node re-run

```
gate_09_budget_consistency   status=pass   fresh=FALSE
  stale input: phase_outputs/phase6_implementation_architecture/implementation_architecture.json
```

The n06 re-run rewrote `implementation_architecture.json`, which `gate_09` records as an input, so
ST-1 content staleness invalidated it. This is the mechanism working correctly, not damage.

**Verified there is no further cascade.** `gate_09` is the only gate consuming a phase-6 output. The
only phase-7 artifact anything downstream reads is `budget_gate_assessment.json`, consumed by
`gate_10a`, which is evaluated after n07 inside the same run. So the chain terminates: **n07 → n08a**.

Do not skip n07 hoping `gate_10a`'s `g09a_p01` will tolerate it. That predicate re-asserts `gate_09`
per §8.4 and the block is unconditional.

### Upstream state (all fresh and passing except n07)

| Phase | Gate | run_id |
|---|---|---|
| 1 | `phase_01_gate` | `11d4fcae` |
| 2 | `phase_02_gate` | `7acc143b` |
| 3 | `phase_03_gate` | `bd337f0b` |
| 4 | `phase_04_gate` | `49159a5c` |
| 5 | `phase_05_gate` | `46f0dc6d` |
| 6 | `phase_06_gate` | `77de89e4` |
| 7 | `gate_09_budget_consistency` | `7b67fe1d` — **STALE, re-run** |

---

## 3. The existing Excellence drafts are dead — use a NEW run-id

`section_drafts/excellence/` holds four drafts and a spine at run-id
`ec01fb84-4d7f-4744-a534-79739a225db2`, `overall_status: unresolved`.

`agent_runtime` reuses drafts when the spine `run_id` matches the current run. **Re-running on
`ec01fb84` would reuse these drafts and skip drafting entirely** — meaning none of §1.3's fixes
apply, and the node fails again. Two claims block them and neither can be cleared:

- `CC_ELTE_TRACK_RECORD_DEFERRED` — a drafter-invented id matching no declaration key and no
  `checklist_ref`. No declaration can reach it.
- `MOBILITY_ELIGIBILITY` — **was** clearable via the new bridge, but is no longer: the
  `mobility_eligibility` declaration was withdrawn when the operator promoted the fact to Confirmed
  (§4). Simulated after the promotion, the applier now rewrites **nothing**.

Plus three `inferred` claims citing `working_assumptions.json` now also fail W2.

A fresh run-id re-drafts (~17 min drafting + ~7 min audit skills) and the fixes apply. Deleting
`section_drafts/excellence/` is optional — a new run-id makes the spine stale and it re-drafts either
way — but deleting is clearer.

---

## 4. Operator decisions taken on 2026-08-14 (do not re-litigate)

- **Mobility eligibility promoted to Assumed → Confirmed** by explicit operator instruction, given
  twice. This required withdrawing the `mobility_eligibility` declaration (21 → 20): a declaration is
  stamped Assumed wherever it surfaces and cannot back a Confirmed record. Four records forbade this
  promotion; they are superseded **in place**, not deleted. Record:
  `decision_log/fieldwise-mobility-confirmed-override_2026-08-14.json`, which names the rules
  overridden and preserves the evidence position (CV face count ~15.81 months vs a 12-month cap; no
  residence document in Tier 3). The concern was raised and answered — **do not raise it again.**
  Eligibility is verified at grant agreement preparation and the operator carries it.
- **The three operator placeholders stay Assumed** (`placement_team_AgroVIR`,
  `contact_person_title_AgroVIR`, `signatory_authority_MVCRI`). They cost nothing at the gate —
  `p06` rejects only `unresolved`, `p11` accepts `assumed` — and they remain flagged in
  `working_assumptions.json _operator_placeholders` for hand correction in the final draft. **They
  will appear in the drafted prose.**
- **C5 narrative divergence accepted.** `selected_call.json` `notes` and `project_summary.json`
  `spine_note` still describe HOST/FELLOWSHIP_TYPE as conditional on C5; the checklist records them
  as unconditional. Both are gate inputs, so rewriting them re-invalidates phases 1, 2 and 4. The
  operator chose the free guard: the drafter is now instructed to take spine-identity confirmation
  status **only** from `confirmation_checklist.json` and never to cite either narrative field.
  Precedence ruling recorded in
  `decision_log/fieldwise-c5-unconditional-and-narrative-revert_2026-08-14.json`. Rewriting those
  fields is the clean close — **batch it with the next re-run phases 1/2/4 need anyway.**

---

## 5. Free checks — run these before spending any quota

All Claude-free. Each takes seconds.

```bash
# Are all seven upstream gates fresh and passing?
py -3.10 -c "
import json; from pathlib import Path
from runner.predicates.gate_pass_predicates import is_gate_fresh
R=Path('.')
for ph,g in [('phase1_call_analysis','phase_01_gate'),('phase2_concept_refinement','phase_02_gate'),
             ('phase3_wp_design','phase_03_gate'),('phase4_gantt_milestones','phase_04_gate'),
             ('phase5_impact_architecture','phase_05_gate'),
             ('phase6_implementation_architecture','phase_06_gate'),
             ('phase7_budget_gate','gate_09_budget_consistency')]:
    d=json.loads((R/f'docs/tier4_orchestration_state/phase_outputs/{ph}/gate_result.json').read_text(encoding='utf-8'))
    r=is_gate_fresh(g,d,R); print(g, d['status'], 'fresh=',r[0], '' if r[0] else r[2])"
```

Also worth knowing:

- **Every `gate_10a` predicate can be evaluated directly** against the current section artifact by
  reading `gate_rules_library.yaml` for the args and calling
  `runner.gate_evaluator.PREDICATE_REGISTRY[fn](**args, repo_root=Path('.'))`. `gate_10a` has no
  semantic predicates (`skipped_semantic: true`), so this reproduces the real verdict exactly.
- **The applier can be simulated on a copy** — copy `working_assumptions.json` and
  `section_drafts/` into a scratch tree and call `apply_assumptions('sim', scratch, 'excellence')`.
  This is how the two dead-draft findings above were established without a run.

### Line endings — a real quota hazard

`git checkout` of a gate-input artifact on Windows rewrites LF → CRLF, which changes the fingerprint
with **zero content change** and silently invalidates upstream gates. This already cost one
diagnosis cycle: `selected_call.json` recorded `sha256:5a689e63…`, the CRLF copy hashed
`sha256:425a0f66…`, and the same bytes as LF hashed back to the recorded value. After any checkout,
stash pop or branch switch touching Tier 3, re-run the freshness check above. A `.gitattributes`
pinning these artifacts to LF would remove the hazard — **filed, not done.**

---

## 6. Readiness assessment

**Tier 3 is in good shape.** Confirmed 236 / Inferred 19 / Assumed 34 / **Unresolved 4**. All four
remaining Unresolved are open *questions*, not facts a section drafts from: the background-IP
question, the thin capacity descriptions, the D5.4 timeline point, and the milestone sequencing
question. Twenty declarations, reader clean, every one registered, invariant green.

**`gate_10a` against the current (stale) section:** 9 of 13 pass, including all four
canonical-preservation predicates (`p07` partners, `p08` deliverables, `p09` canonical titles, `p10`
measurable targets). That is the meaningful signal — the pack fix holds and the prose reproduces
canonical identities correctly. The two content failures (`p06`, `p12`) are both draft-borne and both
addressed by §1.3. The other two (`p01`, `p03`) fail only because `${run_id}` is unsubstituted
outside a real run; they resolve inside one.

**Honest confidence:** the structural causes of both previous failures are closed, and Tier 3 is
materially cleaner than at either attempt. But **drafting is non-deterministic** and the claim set
varies run to run — attempt 1 raised seven unresolved claims, attempt 2 raised two entirely
different ones. Fix 3 instructs against the meta-claim class that produced both blockers but cannot
guarantee it. Treat a clean pass as likely, not certain.

**If it fails again**, diagnose free before re-running:

```bash
py -3.10 -c "
import json,glob
for f in sorted(glob.glob('docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/excellence/*.draft.json')):
    d=json.load(open(f,encoding='utf-8-sig'))
    print(f, [(c['claim_id'],c['status']) for c in d['claim_statuses'] if c['status']!='confirmed'])"
```

Then ask: is the blocking claim a fact (→ needs a Tier 3 answer or a declaration) or a meta-claim
about repository state (→ a fix-3 escape; tighten the drafting instruction, do not declare it away)?

---

## 7. Test suite

Last full run: **27 failed / 4009 passed / 44 skipped** (`py -3.10 -m pytest tests/runner -q -p no:randomly`).

| Count | What |
|---|---|
| 19 | Long-standing baseline — drafting-skill size caps, spec-leanness, graph/vault state drift, transport CLI path. None touch app logic. |
| 1 | `test_excellence_overall_status_not_assumed` — honest red. The live section genuinely has `overall_status: unresolved`. Clears when n08a goes green. |
| 7 | **Open work.** State snapshots from the operator's 2026-08-14 fold, asserting the pre-fold world: status totals, open-item lists, "five deferred capacity fields still named". |

The 7 are not a gate blocker and cost no quota. The authorisation record also still needs
`amendments` entries for the artifacts that fold changed, or that drift is undeclared —
`test_the_authorised_state_is_the_state_on_disk` enforces the pairing and will catch it once the
snapshots are corrected.

**When updating a snapshot test after a fold, update it to the new truth — do not delete it.** The
three guards that forbade the mobility promotion were rewritten, not removed: they now assert the
promotion is applied consistently across both surfaces, the declaration is withdrawn, and the
override is recorded. An *undeclared* promotion still fails, which is what those guards were really
protecting.

---

## 8. Files changed this session (uncommitted)

**Runner:**
- `runner/phase8_canonical_pack.py` — source-key aliasing, `outcomes` added to the backstop.
- `runner/assumption_applier.py` — `_resolve_declaration` bridge + claim_id normalization.
- `runner/decomposed_drafting.py` — three drafting instructions (declaration routing, ledger scope,
  confirmation-status precedence).
- `runner/predicates/criterion_predicates.py` — new `declared_facts_are_not_inferred`.
- `runner/predicates/__init__.py`, `runner/gate_evaluator.py` — W2 export + dispatch registration.
- `.claude/workflows/system_orchestration/gate_rules_library.yaml`, `manifest.compile.yaml` — W2 on
  gates 10a/10b/10c.

**Tier 3** (operator fold + the mobility promotion): `capabilities.json`, `partners.json`,
`roles.json`, `working_assumptions.json`, `confirmation_checklist.json`, `topic_mapping.json`,
`impacts.json`, `training_and_career_development.md`. `selected_call.json` and
`project_summary.json` were reverted to committed text and normalized to LF — **leave them alone.**

**Tier 4 decision log:** `fieldwise-open-items-fold_2026-08-14.json`,
`fieldwise-c5-unconditional-and-narrative-revert_2026-08-14.json`,
`fieldwise-mobility-confirmed-override_2026-08-14.json`, plus `amendments` on
`fieldwise-authorisation_2026-08-12.json` and totals on the authorisation packet.

**Tests:** `test_assumption_applier.py` (+5), `test_w2_declared_not_inferred.py` (new, 10),
`test_phase8_consistency_layer.py`, `test_deterministic_components.py`,
`test_impact_implementation_decomposed_drafting.py`, `test_preseed_suppression_scheduler.py`,
`test_fieldwise_ticket6_fold.py`, `test_fieldwise_ticket7_authorisation.py`.

---

## 9. Do this

```bash
py -3.10 -m runner --run-id <SAME-OR-NEW> --node n07_budget_gate --verbose
# verify gate_09 fresh again (free check, §5)

py -3.10 -m runner --run-id <NEW-UUID> --node n08a_excellence_drafting --verbose
```

`--node` accepts the canonical id or the `8a` shorthand. Expect ~25 minutes for n08a.

**Do not** re-run n01–n06. **Do not** reuse run-id `ec01fb84`. **Do not** hand-edit claim statuses in
a draft to force a green — that is the fabricated completion §15 forbids, and the whole point of the
last two days was to make the honest path work.
