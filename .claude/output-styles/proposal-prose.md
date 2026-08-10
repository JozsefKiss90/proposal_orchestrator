---
name: Proposal prose
description: Claude writes evaluator-facing proposal text in plain, checkable English with short sentences
keep-coding-instructions: true
---

# Writing proposal prose

The full rules are `docs/style/proposal-prose-profile.md`. Read it before drafting or revising Tier 5
prose. It is an execution aid under `CLAUDE.md` §10.2, not an authority: where it appears to conflict
with the constitution or with Tier 1, 2A or 2B, those govern.

## What this style governs

Prose a human reads: the text fields in `docs/tier5_deliverables/`, and Phase 8 section drafts.

It does not govern code, schemas, JSON keys, validation reports, the decision log, or how you use tools.
Do not flatten your engineering judgment to fit a prose rule.

## The reader

An evaluator, scoring many proposals under time pressure. A sentence they must read twice costs a point
somewhere. A claim buried in a 90-word sentence reads as no claim at all.

Measured across the three shipped Tier 5 sections: 1,423 sentences, mean 28.0 words, 46% over 25 words,
288 over 40 words, longest 135, and 426 em-dashes.

## Sentences

- 25 words or fewer. Ceiling of 35, only where a split would change the meaning.
- One idea per sentence.
- Active voice. Name the actor.
- Simple tenses. Present tense for what the project does.
- No noun cluster longer than three words.
- At most two em-dashes per section.
- No semicolon joining two independent clauses. Chained clauses are what produce the 100-word sentences.
- Keep articles and relative pronouns. Cut content, not syntax.

## Paragraphs

- Six sentences maximum.
- The first sentence states the point.
- Delete any sentence whose subject is the document or the section. *This section describes* and *as
  outlined above* carry nothing for an evaluator.
- Tables answer their own question. The reason goes in the cell.
- A bullet holds one or two sentences.

## Terminology

There is no local glossary. Terminology comes from the tiers: programme and instrument terms from Tier 1
and Tier 2A, call and outcome terms from Tier 2B, project and partner terms from Tier 3.

Use the source's term. Do not coin a phrase to carry an idea. Do not use a term in a sense its tier does
not support.

## Length

Tier 2A governs section length, per `CLAUDE.md` §11.2. This style sets no word budget.

When a section runs over its limit, cut content. Do not compress sentences and keep the scope.

## Claims

`CLAUDE.md` §10.5, §11.4, §13.2, §13.3 and §11.5 already govern evidence. Do not restate them; comply.

The style consequence: an unevidenced intensifier is a claim wearing an adverb. *Rigorous validation*
asserts rigour. *Validation against 240 field observations* evidences it. Prefer the number.

## Words to check

Not yet a ban list, and the generic AI-slop list does not apply here — *impact*, *excellence* and
*innovation* are evaluation criteria names.

Watch these, measured as overused in the current drafts: *ensures*, *specifically*, *rigorous*, *state
of the art*, *critical*. Each asserts something a measurement could show instead. *Directly* and
*explicitly* are often legitimate here; check them rather than cutting them.

## How to revise

Two passes, never merged.

1. **Detect.** Name the pattern, quote the line, give the fix in one sentence. Do not rewrite yet.
2. **Edit.** Apply the fixes. Output the revised text and a short "What changed" list.

## When a rule fights the content

Say so. Do not silently break a rule, and do not mangle a true statement to fit a word count. Report the
conflict, propose the smallest change that satisfies both, and let the human decide.

Never report that a deliverable passed a check that did not run.
