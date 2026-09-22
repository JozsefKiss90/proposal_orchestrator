Diagnosis — three independent failures, three different classes

The good news first: drafting itself succeeded this time — all sub-sections parsed, assembly ran, and the gate genuinely evaluated 13 predicates (11 passed, including both prior failure classes W1/p11 and W2/p12 on the directly-declared claims). The three failures are each a different kind of problem, and per the handoff's classification rule, only one of them is fixable by tightening instructions. None of them should be "declared away".

g09b_p06 — communication_addressed: false — upstream Phase-5 gap, not a drafting defect

The section's dec_coverage flags are not derived from the drafted prose. They're computed deterministically at drafting start by source_section_extra_fields() from the Phase-5 impact_architecture.json alone — and that artifact contains no communication_plan key and literally never uses the word "communication". Meanwhile the drafted 2.2 prose covers communication (×6) and public engagement (
3. Dropping the assertion from prose is the one option I'd advise against — the criticized state in the previous evaluation was precisely silence on IP.

g09b_p13 — seniority claim marked inferred — drafting-instruction escape (free fix)

Claim 22 says the placement is "supervised on site by a named senior research-grade member" — the drafter derived seniority from the declared title (placement_supervisor_title_<partner>), called the derivation "inference", and invented its own claim_id, which defeats the assumption-applier's key match. The current prompt only covers "a fact whose only support is an operator declaration"; the model rationalized a fact derived from a declaration as inferred. §12.2 is clear: a derivation from an assumed premise is assumed, not inferred — inference must chain from confirmed evidence. The W2 predicate caught it exactly as designed. Fix: extend the drafter's W2 instruction — "this applies equally to any fact derived from or paraphrasing a declared value; use the declaration's key as claim_id even when your sentence derives from rather than restates it" — plus a prompt-content regression test, same pattern as the quote fix. No quota needed.

Sequencing note

p13 is a free prompt edit; p07 needs your declaration text; p06 needs your route choice (rerun n05 vs. logged amendment vs. oracle redesign). All three must land before the next n08b attempt, because rerun hygiene redrafts everything and the claim set varies per run — and remember run 5dd0e971's manifest now also holds n08b at blocked_at_exit, so the next attempt again needs either a fresh run-id or that one-word manifest reset.

Tell me the p07 declaration wording and your p06 route, and I'll implement all three.