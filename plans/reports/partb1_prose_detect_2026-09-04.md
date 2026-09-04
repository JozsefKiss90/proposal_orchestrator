# Part B-1 condensed form — prose detect pass (2026-09-04)

Pass 1 of the two-pass revision method in `docs/style/proposal-prose-profile.md`. Detection only;
the edit pass is applied separately through `tools/build_partb1_condensed.py` and re-measured.

Scope: the paragraph blocks and the Gantt caption of the Stage-4 condensed content
(commit `8209bcb`, 5,443 words total, 3,710 of them prose). Table cells and the template's own
section headings are measured separately. Measured mechanically (scratchpad `prose_detect.py`,
abbreviation- and decimal-protected sentence splitter); rulings below are judged, and say so.

## Measured state

| Metric | Profile rule | Measured |
|---|---|---|
| Mean sentence length | ≤25 words, ceiling 35 | 26.7 words (139 sentences) |
| Sentences over 25 words | — | 67 (48%) |
| Sentences over 35 words | ceiling breach | 38 (29 of them over 40; longest 81) |
| Em-dashes | ≤2 per section | 64 total (1.1: 15, 1.2: 14, 3.2: 9, 1.3: 7) |
| Sentences containing ';' | no clause-joining semicolons | 37 (see ruling 2) |
| Paragraphs over 6 sentences | ≤6 | 2 (1.1 "beyond state of the art"; 1.2 challenges) |
| Table cells with a sentence over 25 words | tables answer their own question | 15 |
| Watch words | §10 review list | genuine/genuinely 6, precisely 2, rigorous 2, deliberately 2 |

The over-25 rate equals the 46–48% measured on the shipped Tier 5 sections: the condensation
inherited the drafting-era sentence habit even though the content was re-authored.

## Findings by pattern (worst instances quoted; full list in the measurement output)

1. **Colon-plus-inventory sentence.** The 81w CV inventory (1.4: "Her transition into the second
   pillar is already under way…") and the 78w KPI enumeration (2.3: "Delivery is auditable through
   eleven KPIs…"). Fix: keep the inventories, split them into two to four carrier sentences; every
   K1–K11 token must survive individually (builder self-check).
2. **Semicolon chaining of independent clauses.** E.g. 3.1 "The fellow personally executes…;
   partners contribute…", 3.2 "…is HUN-REN ATK; full infrastructure…", caption "There are no
   secondments; the mobility element…". Fix: full stops. **Ruling (judged):** semicolons that
   delimit items of an enumeration after a colon are list punctuation, not clause chaining, and
   stay (e.g. the transferable-skills list, the committed-output set).
3. **Em-dash asides carrying a second idea.** E.g. 1.3 Steering Group sentence (55w, three
   em-dashes), 1.1 "The novelty is not a new machine-learning algorithm — …". Fix: promote the
   aside to its own sentence, or demote it to parentheses/comma; target ≤2 em-dashes per
   criterion section, en-dashes in ranges untouched.
4. **Multi-transition freight sentences.** E.g. 1.1 "The advance is a chain of transitions: …"
   (45w, four "from…to" legs), 1.2 conviction sentence (39w). Fix: two sentences, criteria named
   in the second.
5. **Unevidenced intensifiers (profile §9/§10).** *genuinely out-of-sample*, *deliberately
   compact*, *is strong precisely where*, *this genuine exchange*. Fix: drop or replace with the
   mechanism. **Ruling (judged):** "rigorous predictive modelling…" stays in both occurrences —
   it names the competence gap consistently and sits next to the T1 needle phrase; "state of the
   art" occurs only inside the template's own 1.1 heading (Tier 2A text, exempt).
6. **Over-long paragraphs.** 1.1 beyond-state-of-the-art (7 sentences) and 1.2 methodological
   challenges (7). Fix: split into two paragraph blocks each; no content change.
7. **Table cells.** 15 cells carry a >25w sentence; cells are fragments by design, so only cells
   containing genuine multi-clause sentences are restructured (2.3 Univer cell, 3.2 AgroVIR cell,
   R04 mitigation). Fragment-style semicolon cells stay.

## Declared rule conflicts (profile: report, do not silently break)

- **Word cap vs sentence splitting.** The builder enforces ≤5,450 words for the 10-page limit;
  content sits at 5,443. Splitting ~45 sentences costs words. Resolution: intensifier cuts and
  aside-tightening pay for the splits; the cap stays authoritative and the self-check blocks
  regressions. No scope is cut and no claim is weakened to buy words.
- **Enumerations over 35 words.** Four genuine inventories (four-assumptions sentence,
  committed-output set, transferable-skills list, cadence list) stay above 25 words because a
  split would change meaning (profile §5 ceiling clause). They are flagged here, not hidden.
- **Binding needles.** All builder `require()` needles (A-6 phrase, "citation pending",
  "principal methodological competence gap", "745,000", "month 2", T2 model sentence, EGU/ECPA,
  K1–K11) are preserved verbatim through the edit pass; the self-check enforces this.

## Edit-pass result (pass 2, applied through the builder the same day)

| Metric | Before | After |
|---|---|---|
| Words (whole content) | 5,443 | 5,450 (cap 5,450) |
| Prose sentences | 139, mean 26.7 words | 216, mean 17.2 words |
| Over 25 words | 67 (48%) | 31 (14%) |
| Over 35 words | 38 (longest 81) | 5 (all declared enumerations, longest 45) |
| Em-dashes | 64 | 0 (en-dashes in ranges and labels untouched) |
| Clause-joining semicolons | ~27 of 37 | 0 (10 remaining are list punctuation) |
| Paragraphs over 6 sentences | 2 | 0 (run-in bold lead-ins ruled as labels, not sentences) |

What changed, by class:

- Long sentences were split at clause boundaries.
- Em-dash asides were promoted to sentences or demoted to parentheses.
- The 81w CV and 78w KPI inventories became carrier sentences; every K1–K11 token survives.
- Two duplicated statements were cut to pay for the splits. The open-science motto is stated
  once, and the AgroVIR month-1 consultation is stated where it is load-bearing.
- Unevidenced intensifiers were dropped: *genuinely*, *deliberately*, *precisely*, one *genuine*.

No fact, figure, flag, status marker or claim was added, removed or strengthened. All builder
`require()` needles pass. The builder self-check now enforces the em-dash budget and a 45-word
hard sentence guard permanently.

## What was measured vs judged (profile §13)

Measured: sentence/paragraph lengths, em-dash counts, semicolon counts, watch-word counts, word
total. Judged: list-vs-clause semicolon rulings, enumeration exceptions, intensifier rulings,
active-voice and metadiscourse review (no sentence takes the document or the section as its
subject). No check is
reported that did not run; there is still no repository linter for these rules — the builder's
self-check gains mechanical guards (sentence >40w, em-dash budget) in the edit pass.
