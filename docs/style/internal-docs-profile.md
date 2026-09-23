# The internal documentation profile

## 1 · Status and authority

**This document is an execution aid under `CLAUDE.md` §10.2. It is not an authority.**

It does not redefine a phase, a tier, a gate, or the authority hierarchy. Where it appears to conflict
with the constitution, the constitution governs, per §15.

It governs no deliverable. Tier 5 proposal prose is governed by
`docs/style/proposal-prose-profile.md`, which is a separate document with a different reader.

## 2 · What it governs

Documentation written for a person working on this repository:

- `README.md`, `AGENTS.md`, `Proposal_Engine_Operator_Manual.md`
- `plans/**/*.md` — tickets, milestones, handoffs, reports
- `docs/**/*.md` outside the tier directories — briefs, plans, ADRs, guides, validation reports

It does not govern `CLAUDE.md`, Tier 1 to Tier 5 content, code, schemas, or commit messages.

## 3 · Why this document exists, and what it is not for

Measured across 74 files on 2026-08-08, splitting list items and table cells so a bullet list is never
counted as one sentence:

| Measure | Value |
|---|---|
| Sentences | 8,671 |
| Mean words per sentence | 12.1 |
| Median | 9 |
| Sentences over 25 words | 663 (8%) |

**This corpus is already readable at sentence level.** It is better than the course material this profile
was adapted from, and far better than the Tier 5 sections. A sentence-length campaign here would be
solving a problem that does not exist.

The defects are size and a small number of files.

**The longest documents:**

| File | Words | Mean sentence |
|---|---|---|
| `plans/tickets_phase8_review.md` | 6,674 | 22.4 |
| `docs/backend_migration_plan.md` | 5,819 | 10.1 |
| `docs/chat.md` | 5,530 | 19.8 |
| `AGENTS.md` | 3,997 | 13.6 |
| `plans/tickets.md` | 3,248 | 17.6 |

**The files that do have a sentence problem** (mean over 18, at least 300 words):
`phase_3_readiness_evaulation.md` (25.7), `aws_iam_implentation_steps.md` (25.5), `evaluation_report.md`
(23.0), `tickets_phase8_review.md` (22.4), `tickets_milestone2.md` (20.9), `chat.md` (19.8).

Fix those six. Leave the rest alone.

Two observations that are not style problems and need a decision instead:

- `docs/chat.md` is 5,530 words of what appears to be a pasted transcript. It is not documentation.
  Move it or delete it.
- `phase_3_readiness_evaulation.md` has a typo in its filename.

## 4 · The reader

A colleague, or an agent, who needs to act. They arrive with a question and want the answer without
reading the whole file. Two consequences:

- The answer goes near the top, not after the reasoning that produced it.
- A document that must be read end to end to be useful has the wrong shape.

## 5 · Shape and size, by document type

This is the rule that matters here. Sizes are proposed from current practice, and the last column names
the files that already exceed them.

| Type | Must contain | Budget | Currently over |
|---|---|---|---|
| One ticket | The problem, the acceptance test, the affected files | 250 words | many, inside the ticket files |
| Ticket file | A list of tickets, each within budget. No preamble | no cap | — |
| README | What it is, how to run it, where to go next | 1,500 words | none |
| Plan | The goal, the steps, the exit condition | 2,500 words | `backend_migration_plan.md` |
| ADR | Context, decision, consequences | 800 words | `ADR-001-security-decisions.md` |
| Handoff | State now, what is next, what is blocked | 1,000 words | none |
| Validation report | What ran, what passed, what failed, the numbers | 1,500 words | none |

A document over budget is split, not compressed. Compressing a plan into the same length with denser
sentences is how the six problem files above were made.

## 6 · Sentences

The corpus mean is 12.1 words. The rule targets the tail, not the mean:

- **35 words is the ceiling.** Over that, split.
- Flag anything over 25 in a document whose mean already exceeds 18.
- One idea per sentence. Active voice, and name the actor.
- No semicolon joining two independent clauses.
- No noun cluster longer than three words.

There is no em-dash ceiling here. Internal notes are not published prose, and the count is not the
problem this corpus has.

## 7 · Paragraphs and lists

- Six sentences maximum per paragraph. The first states the point.
- A bullet holds one or two sentences. A bullet holding four is a paragraph wearing a dash.
- A table cell answers the question. The reason goes in the cell, not in a paragraph below it.
- Status labels appear in one table, not scattered through the prose.

## 8 · Delete on sight

- **Writing about the writing.** Any sentence whose subject is the document or the section. *This
  document describes*, *as outlined above*, *the following section covers*.
- **Restating.** A sentence that says again what the previous one said in other words.
- **Preamble in a ticket.** A ticket opens with the problem, not with context the reader already has.
- **Résumé of the reasoning.** A decision record states the decision. The path that reached it goes in
  one short section, or nowhere.

## 9 · Words

**Do not import a ban list from the other profiles.** Measured here, the generic set barely fires:
*robust* 4, *comprehensive* 7, *ensure* and *ensures* 17 combined, *just* 14 across 8,671 sentences.
*leverage*, *streamline*, *seamless*, *holistic* and *cutting-edge* do not appear at all.

Watch two things instead, both of which cost a reader time:

- **`ensure` and `ensures`** where a mechanism would be more useful. *Ensures idempotency* tells the
  reader less than *writes are keyed on run id*.
- **Vague `just` and `simply`** in instructions. If a step is simple, the step shows it.

## 10 · Terminology

Domain vocabulary comes from `CLAUDE.md`: the tier model in §5, the phases in §7, the gates, the
ontology in §4. Use those words with those meanings.

Do not coin a phrase to carry an idea. Do not use a constitutional word in a looser sense — a *gate* is
the thing §7 defines, not any checkpoint.

## 11 · How this differs from the other two profiles

Kept for whoever packages these rules for reuse. The last row is the shared core.

| Rule | Course lessons | Tier 5 proposals | Internal docs |
|---|---|---|---|
| Reader | a learner | an evaluator | a colleague who needs to act |
| Sentence limit | 25 | 25 | 35, flagged at 25 in bad files |
| Length budget | 2,000 words | set by Tier 2A | per document type (§5) |
| Term registry | `wiki/terms/` | the tiers | `CLAUDE.md` §4, §5, §7 |
| Banned words | full list | rejected, re-derived | rejected, two items only |
| Em-dash ceiling | 2 | 2 per section | none |
| Paragraph limit, one idea per sentence, active voice, no metadiscourse, list and table shape | same | same | same |

## 12 · Conformance

There is no linter here yet. The course repository has one at `tools/lesson-lint.mjs` and node 22 is
installed, so the sentence, paragraph, list and metadiscourse checks would port. The budgets in §5 would
need a document-type argument, which that linter does not have.

Until then, say which rules were measured and which were judged. Never report that a document passed a
check that did not run.
