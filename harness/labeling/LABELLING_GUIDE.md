# Materiality labelling guide (E3.1)

You are labelling short text spans as **material** or **not material**, by hand, to test the harness's materiality classifier. Your labels are the *answer key* — the classifier is graded against you.

> **The one rule that makes this valid:** label these **yourself**. Do not ask an AI to label them. The whole point is an independent human check on an AI classifier; if an AI writes the answer key, you're only checking that the AI agrees with itself. (Same discipline as the E1.5 gold set.)

## The one question to ask

For each span: **"Would a grant reviewer expect this statement to be backed by a source — and would the proposal be weaker or misleading if it were wrong?"**

- **Yes → `material: true`** — a substantive, attributable factual claim.
- **No → `material: false`** — connective tissue: framing, transitions, definitions, method description, or generic aspiration that asserts no specific checkable fact.

This is CLAUDE.md §10.5 in practice — *"for each material claim … the Tier 1–4 source from which the claim derives; unattributed claims must be flagged, not asserted."* You are deciding which sentences that rule applies to.

## Material (`true`) — a specific, checkable fact

- Names, roles, affiliations, credentials — "Dr X is a plant physiologist"; "the host is ELTE Budapest".
- Numbers, dates, quantities, targets — "24-month fellowship"; "improves WUE by 25%"; "PhD 2020".
- Capabilities, resources, commitments — "the lab operates a phenotyping facility"; "a secondment in month 14".
- Causal / outcome claims — "adoption could cut water withdrawals by 15%".
- Prior results — "preliminary trials showed r > 0.9".

If any of these were wrong, a reviewer would be materially misled → material.

## Not material (`false`) — connective tissue, no checkable fact

- Transitions / signposting — "The next section describes the methodology."
- Framing / aspiration — "This is a timely and ambitious project."
- Definitions of general terms — "Uncertainty quantification refers to characterising confidence in predictions."
- Restating the call's own language — "In line with MSCA objectives, the action emphasises mobility."
- Method description with no specific claim — "Data will be analysed and results interpreted."
- Hedges / meta-commentary — "It is worth noting that several approaches exist."

## Edge cases (tie-breaks)

- **A number inside framing** → material (the number is checkable): "the target of ≥90% interval coverage".
- **A generic textbook definition** → not material; **a definition tied to a specific value or commitment** → material.
- **Boilerplate compliance** ("will follow FAIR principles") → *not* material unless it makes a specific, checkable commitment.
- **Genuinely 50/50** → mark `material: true` and add a `note`. Erring toward "material" makes the test stricter, which is the safe direction here.

## How to record

Set the `material` field in each JSONL row to `true` or `false`; add a one-line `note` for tricky calls. Leave `material: null` only if you truly can't decide — the loader is fail-closed, so `null` rows are simply not counted.

## Two files, two jobs

- **`materiality_negatives_*.jsonl`** — spans expected **not** material. Confirming these measures the **false-alarm rate (precision)**: does the classifier wrongly call framing "material"?
- **`materiality_escapes_SEED.jsonl`** — spans expected **material** but **not in the ledger** (invented facts a drafter might slip in). Confirming these measures the **miss rate (recall)** on the real threat: does the classifier wave a real claim through? For each seed, also set `in_ledger: false` **after checking it against the 406-claim ledger** — if it turns out to be logged, it isn't an escape; drop it or set `in_ledger: true`.
