# V09 completion report, second pass — the 2025 authorities retrieved and the matrix re-derived

| Field | Value |
|---|---|
| Date | 2026-10-13 |
| Branch | `msca-dn-pre-eval` |
| Ticket | V09, gate G3 |
| Supersedes | `plans/reports/v09_authority_matrix_2026-10-12.md` |
| Decision record | `docs/tier4_orchestration_state/decision_log/msca-dn-authority-matrix_2026-10-13.json` |
| Status | Agent-drafted. Acceptance is the operator's. |

The first pass declared four 2025 documents absent and six rows defaulted. Three of those documents
have since been retrieved from their issuing body. This report records what they changed.

The earlier report stands as written. It describes what was true on 2026-10-12, and the index and
matrix it describes are still in the tree, unedited.

## 1. What the operator authorised

The operator instructed on 2026-10-13 that the documents be found online, and authorised downloading,
inspecting, storing and indexing them. Ticket V09's wording reserving supply to the operator is
amended by that instruction.

Four constraints came with it, and each shaped the work:

- Record provenance accurately: address, retrieval date, the title, version and date the document
  gives itself, the computed hash, and any captures or corroborating copies.
- Do not label a retrieval `operator_supplied` or `issuer_hash_confirmed`.
- Separate byte integrity, source authenticity and historical applicability.
- Do not promote a claim to Confirmed because a document arrived.

## 2. The three documents

| Document | Identity | Origin | Place in the call |
|---|---|---|---|
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | Work Programme 2023-2025 part 2, Decision C(2025) 2779 of 14 May 2025, 158 pages | Retrieved from the published address, and byte-identical from the issuing body's second site | Stated by the document: page 23 names the call, its opening and its deadline |
| `wp-14-general-annexes_horizon-2025_en.pdf` | Work Programme 2025 part 14, same Commission Decision, 44 pages | Placed by the operator, then read from the published address; the bytes agree | Stated by the cover, under the same decision as the part above |
| `ef_he-msca_v2.0_2025-02-28.pdf` | Evaluation Form (HE MSCA) version 2.0, 9 pages | An archive of the published address, which now serves a later version | **Bracketed, not closed** |

The work programme carries the call's own conditions and topic text at pages 23 to 26. So no separate
call document is stored, and the index declares no destination for one. A second file duplicating
pinned pages would add bytes to keep in agreement and nothing to the evidence.

The work programme's published filename says 2023-2024. Its cover says the 2023-2025 edition and
carries the 2025 decision. It is stored under the edition it declares, and the index records why.

### 2.1 Why the evaluation form's era is not settled

The published template address serves whichever version is current. Three captures of it carry one
archive digest, dated 2025-06-19, 2025-10-03 and 2025-11-05. The call opened on 28 May 2025 and
closed on 25 November 2025, so the last capture is twenty days inside the window. The next distinct
digest is 2026-03-12, months after the deadline.

That brackets the window without closing it. A version served between two captures and never captured
would leave no trace here. The captures are also of one archive, so they are one witness observed
three times rather than three witnesses.

Row EI-02 therefore stays `unresolved`, and every row citing that form is Inferred.

## 3. One field was answering three questions

`authentication` recorded how a source's bytes are vouched for. A file retrieved from the issuing
body's address is hashed in this tree exactly as a file of unknown origin is. So byte integrity could
not distinguish them, and neither question says whether the document governed a closed call.

Recording a retrieval as `operator_supplied` would have been false. Recording it as
`issuer_hash_confirmed` would have been a fabrication.

The index schema moves to `authority_source_index/2` and each entry now answers three questions:

| Question | Field | What settles it |
|---|---|---|
| Are the bytes fixed? | `authentication` | A hash — the issuing body's, the operator's word, or this tree's own |
| Are they the issuing body's? | `source_authenticity` | A retrieval, a second independent copy, an archive of the address |
| Was this in force then? | `historical_applicability` | The document saying so. Retrieval dates cannot: bytes fetched today evidence today |

**The authentication vocabulary gained no rank.** A retrieved document stays `computed_only`, so it
still cannot carry a Confirmed row. That is the smallest amendment that holds: the new evidence goes
in new fields rather than by promoting the old one.

A `provenance` block records the acts — the address, what was read, when, the document's own title,
version and date, the captures, the second copies.

### 3.1 A rank must be carried by its record

Each answer above `unrecorded` names what it rests on, and the record must carry it. Four findings
were added to the reader:

| Finding | What it catches |
|---|---|
| `authenticities_claimed_without_a_basis` | An origin claimed with no sentence saying what the evidence is |
| `applicabilities_claimed_without_a_basis` | The same for an era claim |
| `ranks_unsupported_by_their_provenance` | Corroboration with neither a capture nor a copy recorded |
| `confirmed_on_inconclusive_applicability` | A Confirmed row citing a source whose era is bracketed |

The last one is the teeth of the third axis. Byte integrity and origin can both be settled while a
document's place in a closed call is not, and a confirmation resting there confirms a wording.

A declared second copy whose hash is not the stored file's is refused outright. A copy with other
bytes corroborates nothing.

### 3.2 Older indexes stay readable

The reader accepts both schemas. A version-1 entry declares none of the three fields, and reads as a
held file with no recorded origin and no established place in its era. That is what declaring nothing
means, and reading one as corroborated would lend the successor's evidence backwards.

`TestTheSuccession` asserts the 2026-10-12 pair still loads and still checks green.

## 4. The six defaultings, re-derived

| Row | Was | Now | What states it |
|---|---|---|---|
| CR-02 — which criterion each aspect is graded under | defaulted | equivalent | The 2025 form, measured: each of the ten aspect texts falls inside its own criterion's section |
| WT-02 — weighting serves the ranking, not the pass | defaulted | equivalent | The 2025 form, word for word the same sentence |
| TH-03 — which authority sets the overall threshold | defaulted | equivalent | Three 2025 documents point the same way |
| TH-05 — the score resolution | defaulted | equivalent | Decided by a recorded score, below |
| EI-01 — the six score-level descriptions | defaulted | equivalent | All six sentences occur verbatim in the 2025 form |
| EI-04 — the applicability-tag grammar | defaulted | equivalent | The 2025 form carries it, and CR-02 measures the selection |

Nine other rows gained a 2025 citation without changing verdict. The weights, the maximum, the
per-criterion threshold, the overall threshold and the criteria names are now stated by the call's own
documents rather than inferred from the result alone.

### 4.1 CR-02 is measured, not read off a list

Presence is not grouping. All ten aspect texts could be in the document and sit under the wrong
criterion, which is the claim the row actually makes.

The deriver walks the 2025 form once, locates its three criterion section headings, and requires every
aspect text to fall inside its own criterion's section. A heading occurring twice gives no boundary and
refuses. An aspect present but grouped elsewhere refuses.

### 4.2 The two 2025 authorities disagree about the resolution

The work programme states a resolution of one decimal place. The evaluation form of the same call
window states that half marks may be given. Both are 2025 authorities and they do not agree.

The recorded result decides which was applied. Two of the three criterion scores are 4.2, and no
half-mark rule could award that.

The deriver refuses to render the row if no recorded score is finer than a half mark. If every score
happened to be a half mark, both rules would fit, and the equivalence would again be an absence of
visible difference read as agreement.

What is settled is the rule applied to this submission. The conflict itself is not resolved, and the
decision record logs it as a tier conflict under CLAUDE.md §12.3.

## 5. One row was added

TH-06 records a difference the retrieval revealed. The 2025 evaluation form prints an unweighted total
out of 15, with an overall threshold of 10 points. The 2026 form states the threshold on the weighted
total out of 100.

The difference is in the forms, and it is not the rule that governed. The call's work programme sets
the threshold at 70% of the weighted total, and the recorded result is a weighted total out of 100. So
the form's generic total was superseded by the call's own rule.

The evaluation form supplies the ground for that itself: it states that specific calls or topics may
have different rules.

## 6. What is still open

Five limitations are preserved, not closed:

- No entry carries a hash published by its issuing body, so **no row is Confirmed**.
- The 2025 evaluation form's place in the call is bracketed. Every row citing it is Inferred.
- The 2025 application form has no recorded origin and no established place in the call. No
  corroborating copy was sought for it, and five rows cite it.
- The submission's binding to a call identifier is declared, not evidenced. CI-01 stays Assumed, and
  the one remaining index absence is the record that would settle it.
- The resolution conflict is resolved for this submission only.

Two more, unchanged from the first pass: whether each area's rows are all of its scoring-relevant
rules is the author's judgement, and the acceptance lane was not run.

## 7. The numbers

| Measure | First pass | Now |
|---|---|---|
| Rows | 26 | 27 |
| Equivalent / differs / defaulted / unresolved / era-neutral | 12 / 1 / 6 / 2 / 5 | 18 / 2 / 0 / 2 / 5 |
| Inferred / Assumed / Unresolved / Confirmed | 18 / 7 / 1 / 0 | 25 / 1 / 1 / 0 |
| Documents obtained, of indexed | 12 of 16 | 15 of 16 |
| Verified document quotes | 35 | 74 |
| Reader findings | 25 | 29 |

## 8. Checks run

| Check | Result |
|---|---|
| `tools.author_msca_dn_authority_matrix --check` | `up to date` — byte-equal replay |
| `harness.commands.authority_matrix --check` | green over 29 findings |
| `tests/test_msca_dn_authority_matrix.py` | 79 passed |
| `tests/harness/test_authority_matrix.py` | 75 passed |
| `tests/test_msca_dn_declaration_drafts.py` | 82 passed |
| The superseded pair | loads under schema 1 and checks green |

No assessor ran. No runner phase was dispatched. No quota was spent, and the 74.60 baseline is
untouched.

### 8.1 One other ticket's artifact had to be re-rendered again

The successor index pins the sanitised revision's register by hash, so the R04 adoption-cost scan
found three further dependents. The declaration drafts and their checklist were re-rendered and a
successor re-render record states the two moved hashes.

That record names no register path. A record that named one would make the drafts stale again.

### 8.2 One superseded reading was re-rendered

`authority_source_index_2026-10-12.md` changed, because a reading is rendered by the reader and the
reader gained the three axes. The declaration's bytes are unchanged.

Its reading now reports that index's entries as origin unrecorded, which is what that declaration
says. Leaving it as written would have committed a rendering no reader produces.

## 9. What this is not evidence of

- That the 2025 evaluation would score the sanitised text the same way.
- That the harness's scoring method is correct.
- That the retrieved documents are authentic in the sense an issuing body's hash would establish. They
  are corroborated, which is less.
- That V09 is accepted. Acceptance and the `review_state` move are the operator's.

## 10. Artifacts

| Path | What |
|---|---|
| `docs/tier2b_topic_and_call_sources/work_programmes/msca/wp-2-msca-actions_horizon-2023-2025_en.pdf` | The 2025 work programme part |
| `docs/tier1_normative_framework/programme_guidance/wp-14-general-annexes_horizon-2025_en.pdf` | Its General Annexes |
| `docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_v2.0_2025-02-28.pdf` | The 2025 evaluation form |
| `docs/tier4_orchestration_state/msca_dn/authority/authority_source_index_2026-10-13.json` + `.md` | The successor index |
| `docs/tier4_orchestration_state/msca_dn/authority/equivalence_matrix_2025_2026-10-13.json` + `.md` | The successor matrix |
| `docs/tier4_orchestration_state/decision_log/msca-dn-authority-matrix_2026-10-13.json` | This work's decision record |
| `docs/tier4_orchestration_state/decision_log/msca-dn-declaration-draft-rerender_2026-10-13.json` | The forced re-render |
| `harness/authority_matrix.py` | The reader, with the three axes |
| `harness/HARNESS.md` | The amendment, documented |
| `tools/author_msca_dn_authority_matrix.py` | The deriver |
