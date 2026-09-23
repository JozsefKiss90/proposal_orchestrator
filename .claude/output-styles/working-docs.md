---
name: Working docs
description: Claude writes tickets, READMEs, plans and handoffs a colleague can act on without reading the whole file
keep-coding-instructions: true
---

# Writing internal documentation

The full rules are `docs/style/internal-docs-profile.md`. It is an execution aid under `CLAUDE.md`
§10.2, not an authority. Where it appears to conflict with the constitution, the constitution governs.

## What this style governs

Documentation for a person working on this repository: `README.md`, `AGENTS.md`, the operator manual,
`plans/**/*.md`, and `docs/**/*.md` outside the tier directories.

It does not govern Tier 5 proposal prose, which has its own reader and its own style. It does not govern
`CLAUDE.md`, tier content, code, schemas, or commit messages. Do not flatten your engineering judgment
to fit a prose rule.

## The reader

A colleague, or an agent, who arrives with a question and needs to act. They should not have to read the
whole file to get the answer.

Put the answer near the top. A document that only works read end to end has the wrong shape.

## Size and shape first

This corpus is already good at sentence level: mean 12.1 words, median 9, 8% over 25 words. **Size is
the defect, not sentence craft.** Do not run a sentence-length campaign here.

| Type | Must contain | Budget |
|---|---|---|
| One ticket | Problem, acceptance test, affected files | 250 words |
| README | What it is, how to run it, where next | 1,500 words |
| Plan | Goal, steps, exit condition | 2,500 words |
| ADR | Context, decision, consequences | 800 words |
| Handoff | State now, what is next, what is blocked | 1,000 words |
| Validation report | What ran, what passed, what failed, the numbers | 1,500 words |

Over budget means split, not compress. Denser sentences at the same scope is how a document gets worse
while looking shorter.

## Sentences

- 35 words is the ceiling. Over that, split.
- Flag anything over 25 only in a document whose mean already exceeds 18.
- One idea per sentence. Active voice, and name the actor.
- No semicolon joining two independent clauses.
- No noun cluster longer than three words.

There is no em-dash ceiling here. These are working notes, not published prose.

## Paragraphs and lists

- Six sentences maximum. The first states the point.
- A bullet holds one or two sentences.
- A table cell answers its own question. The reason goes in the cell.
- Status labels go in one table, not scattered through prose.

## Delete on sight

- Sentences whose subject is the document: *this document describes*, *as outlined above*.
- A sentence restating the previous one in other words.
- Preamble in a ticket. Open with the problem.
- The path that reached a decision. State the decision; the reasoning gets one short section or none.

## Words

Do not import a ban list. Measured here, the usual suspects barely appear. Watch two things:

- `ensure` and `ensures` where a mechanism is more useful. *Writes are keyed on run id* beats *ensures
  idempotency*.
- `just` and `simply` in instructions. If a step is simple, the step shows it.

## Terminology

Domain words come from `CLAUDE.md`: the ontology in §4, the tier model in §5, the phases and gates in
§7. Use those words with those meanings. Do not coin, and do not use a constitutional word loosely — a
*gate* is what §7 defines, not any checkpoint.

## How to revise

Two passes, never merged.

1. **Detect.** Name the pattern, quote the line, give the fix in one sentence. Do not rewrite yet.
2. **Edit.** Apply the fixes. Output the revised text and a short "What changed" list.

## When a rule fights the content

Say so. Do not silently break a rule, and do not mangle a true statement to fit a budget. Report the
conflict, propose the smallest change, and let the human decide.

Never report that a document passed a check that did not run.
