# g09b_p07 — declaration options for placement IP ownership

**RESOLVED 2026-08-15: the operator approved Option C.** Applied with all six syncs; see `docs/tier4_orchestration_state/decision_log/fieldwise-placement-ip-declaration_2026-08-15.json`. Options A, B and D below are kept as the record of what was offered, not as live choices.

**Decision needed:** one declaration text for `working_assumptions.json` that closes the open background-IP question behind the `PLACEMENT_IP_OWNERSHIP` unresolved claim (run `5dd0e971`, impact §2.2, claim index 45).
**Approve exactly one option.** The approved `value` becomes the exact claim wording in the ledger, because the assumption-applier rewrites the claim with the operator's declared wording before assembly.

## What the declaration must answer

The confirmation checklist carries the operator's own open item: §2.2 records the DrR components as the fellow's background IP, and the proposal does not address ownership of work done on them inside a commercial partner. The drafter surfaced this item and wrote a mechanism nothing in Tier 1–4 states: ownership "to be settled by written agreement between the fellow, ELTE and AgroVIR" before the placement begins. The declaration adopts an answer as Assumed, which is honest under §12.2 and clears p07, because p07 rejects only `unresolved`.

Two constraints govern the wording. First, never declare a fact that is Confirmed elsewhere in Tier 3, because the reader stamps every declaration Assumed and would contradict the Confirmed record inside one tier. ELTE's host status is Confirmed, so it may appear only as context, not as declared substance. Second, a declaration about AgroVIR's position relays something the operator knows about a third party; declare only what AgroVIR has actually accepted or what the operator will obtain from them.

## Option A — process only: a written agreement will settle it

```json
{
  "key": "placement_ip_ownership",
  "value": "Ownership of results generated during the six-month AgroVIR placement will be settled by a written agreement between the fellow, ELTE and AgroVIR, concluded before the placement begins.",
  "declared_by": "operator (p07 resolution, 2026-08-15)",
  "declared_on": "2026-08-15T00:00:00Z",
  "rationale": "The background-IP open item asks how ownership of work done on the fellow's DrR components inside a commercial partner is handled. The operator commits to a signed agreement before the placement rather than to an allocation, because no allocation has been agreed with AgroVIR yet. Declared rather than Confirmed because the agreement does not exist; only its conclusion is promised."
}
```

Commits to a process, not an outcome, so it declares nothing on AgroVIR's behalf beyond willingness to sign. It matches what the drafter already wrote, so the prose survives with minimal drift. The weakness is evaluative: the previous evaluation criticised an insufficiently substantiated IP strategy, and a pure deferral answers the question by promising to answer it.

## Option B — substantive allocation: results vest in ELTE, AgroVIR takes no ownership

```json
{
  "key": "placement_ip_ownership",
  "value": "Results generated during the AgroVIR placement vest in ELTE as the beneficiary employing the fellow; the placement work is training-oriented and AgroVIR acquires no ownership of placement results or of the fellow's DrR background IP, receiving only the access needed to host the placement.",
  "declared_by": "operator (p07 resolution, 2026-08-15)",
  "declared_on": "2026-08-15T00:00:00Z",
  "rationale": "The operator relays the agreed allocation: the placement is training-oriented, so results follow the grant's beneficiary-ownership logic and the company takes nothing. Declared rather than Confirmed because AgroVIR's acceptance is relayed by the operator and no written agreement or company confirmation is in Tier 3. Choose this option only if AgroVIR has actually accepted this position."
}
```

The strongest evaluator answer, because it states an allocation and closes the open item substantively. The risk is third-party consent: it declares AgroVIR's acceptance of a no-ownership position. If that acceptance does not exist yet, this option relays something nobody has said, which is the placeholder failure mode, not a declaration.

## Option C — hybrid: grant-default allocation, agreement confirms it *(recommended)*

```json
{
  "key": "placement_ip_ownership",
  "value": "Ownership of placement results follows the grant agreement default, vesting in ELTE as the beneficiary acting through the fellow; a written placement agreement between the fellow, ELTE and AgroVIR, concluded before the placement begins, will confirm this allocation and the access terms to the fellow's DrR background IP.",
  "declared_by": "operator (p07 resolution, 2026-08-15)",
  "declared_on": "2026-08-15T00:00:00Z",
  "rationale": "Answers the open item with an allocation the evaluator can assess while committing AgroVIR only to signing a confirmatory agreement. The allocation leans on the grant's default results-ownership rule rather than on a negotiated position, so nothing is relayed on the company's behalf except the agreement itself. Declared rather than Confirmed because the agreement does not yet exist and the default's application to this placement is the operator's adoption, not an extracted Tier 1 rule."
}
```

States an allocation, so the previous evaluation's criticism is answered, while the only third-party commitment is a signature on a confirmatory document. If a Tier 1 extraction later confirms the MGA default as a rule, the fact can be promoted and the declaration withdrawn, following the mobility-eligibility precedent of 2026-08-14.

## Option D — placeholder: unknown for now, corrected by hand before submission

Option A's JSON, plus registration under `_operator_placeholders.keys`, marking it as standing in for something nobody has supplied. Choose this only if the arrangement is genuinely undecided; it adds one more placeholder to hand-correct in the final prose, alongside the five already tracked from n08a.

## Syncs required with any option — applied after approval, not before

1. Append the approved entry to `declarations` in `working_assumptions.json`, with an `_extended_by`-style note recording the instruction.
2. Add the key to the declared-keys list in `decision_log/fieldwise-authorisation_2026-08-12.json`, because the packet invariant requires that list to match `working_assumptions.json` exactly and a test fails on drift.
3. Record the fingerprint change as an `amendments` entry on the authorisation record, because undeclared Tier 3 drift fails a test.
4. Update the checklist open item (`open_for_authorisation`, the background-IP entry) from Unresolved to answered-by-declaration, naming the key.
5. Write a decision-log entry for the resolution (§9.4).
6. `checklist_ref` is omitted from the entries above because the open item carries no checklist token; if token routing is wanted, the item needs a token first.

## What this does not fix

p06 (Phase-5 communication gap) and p13 (drafter instruction on declaration-derived facts) are separate failures with separate fixes; see `n08b_fail_diag.md`. The next n08b run redrafts every sub-section, and the drafter must key the IP claim to `placement_ip_ownership` for the applier to flip it to Assumed.
