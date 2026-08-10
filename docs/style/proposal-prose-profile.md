# The proposal prose profile

## 1 · Status and authority

**This document is an execution aid under `CLAUDE.md` §10.2. It is not an authority.**

It does not redefine a phase, a tier, a gate, or the authority hierarchy. Where it appears to conflict
with `CLAUDE.md`, the constitution governs, per §15. Where it appears to conflict with Tier 1, Tier 2A or
Tier 2B, those sources govern, per §3.

It is deliberately not self-binding. `CLAUDE.md` §13.6 forbids a skill from becoming a de facto
constitutional authority, and §14.5 reserves amendment to explicit human instruction. Section 12 below
supplies draft amendment text. Only a human may adopt it.

## 2 · What it governs

Prose written for a human reader in:

- `docs/tier5_deliverables/proposal_sections/*.json` — the text fields, not the keys
- `docs/tier5_deliverables/assembled_drafts/*.json`
- `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/`

It does not govern code, schemas, JSON keys, validation reports, the decision log, or agent instructions.

## 3 · Why this document exists

Measured across the three shipped Tier 5 sections on 2026-08-08, counting sentences inside each text
field and never across fields:

| Section | Words | Sentences | Mean words per sentence | Over 25 words | Over 40 words | Longest | Em-dashes |
|---|---|---|---|---|---|---|---|
| Excellence | 18,805 | 662 | 28.4 | 326 | 137 | 112 | 190 |
| Impact | 13,068 | 412 | 31.7 | 221 | 109 | 118 | 161 |
| Implementation | 8,041 | 349 | 23.0 | 110 | 42 | 135 | 75 |
| **All** | **39,914** | **1,423** | **28.0** | **657 (46%)** | **288** | **135** | **426** |

Nearly half of all sentences exceed 25 words. The median is 23, so the mean is pulled up by a long tail:
288 sentences run past 40 words, and the longest is 135.

## 4 · The reader

An evaluator, reading many proposals against a scoring form, under time pressure. Three consequences:

- A sentence the evaluator must read twice costs a point somewhere.
- A claim whose evidence is buried in a 90-word sentence reads as no claim at all.
- Effort spent decoding syntax is effort not spent scoring the content.

`CLAUDE.md` §11.1 already requires deliverables to be evaluator-oriented. This profile is how that reads
at sentence level.

## 5 · Sentences

- **25 words or fewer.** Ceiling of 35, only where a split would change the meaning.
- One idea per sentence.
- Active voice. Name the actor. *The consortium validates* beats *validation is undertaken*.
- Simple tenses. Present tense for what the project does.
- No noun cluster longer than three words.
- **At most two em-dashes per section.** There are currently 426.
- No semicolon joining two independent clauses. The measured text uses semicolons to chain three and four
  clauses into one sentence, which is where the 112-word and 135-word sentences come from.
- Keep articles and relative pronouns. Cut content, not syntax.

## 6 · Paragraphs

- Six sentences maximum.
- The first sentence states the point.
- No sentence whose subject is the document, the section, or the wording. *This section describes…* and
  *as outlined above* carry no information for the evaluator.
- A table answers its own question. The reason belongs in the cell.
- Bullets hold one or two sentences. A bullet holding four is a paragraph wearing a dash.

## 7 · Terminology

There is no local glossary in this repository, and this profile does not create one. Terminology comes
from the tiers:

| Term type | Authoritative source |
|---|---|
| Programme and instrument terms | Tier 1, Tier 2A |
| Call, topic, outcome and impact terms | Tier 2B |
| Project, partner and capability terms | Tier 3 |

Three rules follow:

1. **Use the source's term.** If Tier 2B calls it an *expected outcome*, the deliverable calls it an
   expected outcome.
2. **Do not coin.** A phrase invented to carry an idea is unreadable to an evaluator and untraceable
   under §10.5. Name the idea in ordinary words.
3. **Do not redefine.** A term used in a sense the tier does not support is a §13.2 or §13.3 problem
   before it is a style problem.

## 8 · Length

**This profile sets no word budget.** Section length is governed by Tier 2A, per `CLAUDE.md` §11.2, and
by the page limits in the application form. That is a stronger constraint than any number chosen here,
and it comes from an authority this document is subordinate to.

The rule that does apply: when a section exceeds its Tier 2A limit, cut content. Do not compress
sentences and keep the scope. Compressed prose at the same scope is how a 40-word sentence is born.

## 9 · Claims

`CLAUDE.md` already governs this and this profile does not restate it: §10.5 requires every material
claim to be traceable to a tier, §11.4 forbids introducing facts not grounded in a higher tier, §13.2 and
§13.3 forbid invented call constraints and project facts, and §11.5 requires a gap to be flagged rather
than filled.

The style consequence is narrow. An unevidenced intensifier is a claim wearing an adverb. *Rigorous
validation* asserts rigour; *validation against 240 field observations* evidences it. Prefer the number.

## 10 · Words to review

**This is not yet a ban list.** The list from the course profile does not transfer: *leverage*,
*streamline*, *transformative* and *harness* appear at most twice each across 40,000 words, while
*impact*, *excellence* and *innovation* are evaluation criteria names and must not be banned.

These are the words this corpus actually overuses. Each needs a human ruling before it becomes a rule,
because several are load-bearing in this domain:

| Word | Count | Note |
|---|---|---|
| directly | 41 | Often legitimate: evaluation forms ask that criteria be addressed directly |
| ensures | 18 | Usually an unevidenced claim. Prefer the mechanism that ensures it |
| explicitly | 13 | Often legitimate: §12.2 requires explicit declaration |
| specifically | 13 | Usually filler before a detail that is already specific |
| rigorous | 12 | Asserts a quality. Prefer the measurement |
| state of the art | 10 | Check each one against a Tier 2B or Tier 1 source |
| critical | 9 | Asserts importance. Prefer the consequence of failure |

Derive the final list from the first review pass, not from this table.

## 11 · What did not transfer from the course profile

Recorded so the shared parts stay honest when these two profiles are compared:

| Course rule | Here |
|---|---|
| Technical Names registry at `wiki/terms/` | No registry. Terminology comes from the tiers (§7) |
| 2,000-word budget | Tier 2A governs length (§8) |
| Bounded closing compression | Not applicable. Application forms set the structure |
| Diagram requirement per artefact | Not applicable |
| Scenario step glosses | Not applicable |
| Banned-word list | Rejected wholesale. Re-derived in §10 |
| Sentence, paragraph, voice, metadiscourse, formatting rules | Transferred unchanged |

The last row is the candidate shared core if these rules are ever packaged for both repositories.

## 12 · Draft amendment, for human adoption only

`CLAUDE.md` §14.5 reserves amendment to explicit human instruction. This text is a proposal, not an
enactment. It is written to satisfy §14.2, which requires an amendment to identify the section, the prior
rule, the new rule, the reason, and the impacted components.

> **Section amended:** 11. Deliverable Rules.
> **Prior rule:** none. §11 governs orientation, compliance, consistency and derivation, and is silent on
> readability.
> **New rule 11.6:** Tier 5 prose must be readable by an evaluator at first pass. Sentences of 25 words
> or fewer, paragraphs of six sentences or fewer, active voice, and terminology drawn from the tiers as
> §7 of `docs/style/proposal-prose-profile.md` sets out. A deliverable that fails these constraints is
> not compliant with §11.1, whatever its content.
> **Reason:** measured across the three shipped Tier 5 sections, 46% of sentences exceed 25 words and 288
> exceed 40. §11.1 requires evaluator orientation but nothing made it checkable.
> **Impacted components:** the Phase 8 drafting and review workflow, any skill producing Tier 5 prose,
> and the Tier 5 review checklist in §12.5.

## 13 · Conformance

There is no linter for this repository yet. The course repository has one at `tools/lesson-lint.mjs`,
and node 22 is installed here, so roughly half its checks would port: sentence length, paragraph length,
em-dash count, metadiscourse and formatting. The term gate, the word budget and the course-specific
checks would not.

Until a linter exists, state which rules were measured and which were judged. Never report that a
deliverable passed a check that did not run.
