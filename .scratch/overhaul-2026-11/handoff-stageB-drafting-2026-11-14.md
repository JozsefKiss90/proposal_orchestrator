# Handoff — Stage B drafting lane, MSCA-DN 2026 resubmission

**Written:** 2026-11-14, by the operator's assistant chat, for the operator and the Claude Code session.
**State:** proposal, not yet decided. Nothing here is executed.
**Deadlines:** internal draft to the consortium 2026-11-16. Call HORIZON-MSCA-2026-DN-01 closes
2026-11-24, 17:00 Brussels time.

This file holds no private material. It names no partner, no person and no number from the 2026 inputs. The
checklist the operator shared names partners; those names stay in the private copy of the master template.

**What the assistant read:** the consortium's `check_list.docx`, the sanitised 2025 proposal, the sanitised ESR,
`af_he-msca-dn_en.pdf` in Tier 2A (V5.0, 29 April 2025), runbook sections 7 and 8, ticket V16, the host
templates. It did not read anything under the private root.

---

## A. Decisions the operator has to give first

| # | Decision | Recommendation | Why |
|---|---|---|---|
| A1 | V15 before this lane? | **Defer, do not skip.** Start drafting now. Sign V15 before the pre-evaluation. | V16 is `Blocked by: V15`. Drafting text is not the V16 assessment. V15 is a record the session drafts and the operator signs; it needs no AWS. |
| A2 | Constitution, sections 8.4 and 13.4 (no Phase 8 activity before the budget gate) and runbook section 7 (revisions are implemented by the named humans) | An explicit, named, in-session instruction that this lane is a private revision of a submitted proposal, run outside the DAG, with AI drafting from human-approved inputs and human confirmation of every new fact. | Without it the session must refuse or halt. The constitution allows a named override for the scope of one instruction only. |
| A3 | Drafting model | **Claude Opus 5.5** through `eu.anthropic.claude-opus-5-5`. | See section B. GPT-6 Astra cannot run on the present route. |
| A4 | Text-polishing pass | Allowed as a second pass, with the guards of section F and a truthful entry in Part B2 section 10. | See section C. |
| A5 | Processing authority for the 2026 material | A new authority statement, as P2 was for V14, covering partner data and the clinical-dataset descriptions. | The 2026 files hold other parties' material. V14's statement covered the 2025 Part B only. |
| A6 | How drafts leave the host | A designed outbound route (section D, step 0.6). | V14 allowed metadata only (V14-OP2). Drafts must reach the consortium. V14-D3 showed what happens without a route. |
| A7 | RAISE DN opt-in | Consortium decision. Out of scope unless the operator says otherwise. | The 2026 form (V6.0) adds a section 11 for it. |

---

## B. Model choice

| | Claude Opus 5.5 | GPT-6 Astra |
|---|---|---|
| Bedrock profile usable from the stack | `eu.anthropic.claude-opus-5-5` (EU geography) | Only `us.` and `global.` profiles. No EU profile. |
| Fits the stack as built | By design yes: `50-secret.yaml` accepts only `eu.anthropic.claude-…` model ids. The host's endpoint policy lists profile and model ARNs by parameter (`InferenceProfileArns`, `FoundationModelArns`), so the Opus 5.5 ARNs must be added there, with a successor to decision OD7. | No: OD7-global excludes `global.` profiles, the id pattern refuses it, and no EU profile exists. It would need new decisions and a route that leaves the EU geography. |
| List price per 1M tokens, in / out | 4.40 / 22 USD (EU profile) | 10 / 50 USD (global), 11 / 55 USD (US) |

Prices are from third-party price listings dated October 2026. Confirm them on the AWS pricing page before the go.

The pre-evaluation keeps the assessor pinned for V14, `eu.anthropic.claude-sonnet-4-6`. The drafter and the
assessor are then different models, and the stage-B result is read under the same assessor as the stage-A
baseline.

**To check in the account:** model access for Opus 5.5 is enabled, and the request and token quotas of the EU
profile (Sonnet 4.6 had 10 requests a minute).

---

## C. The polishing tool

`AIScientists-Dev/academic-humanizer` (v0.3.2, MIT) is **not an MCP server**. It is a skill: a `SKILL.md` and
examples, read by whatever agent runs it. It calls no service of its own.

- On the host it is used as a rule set in a second Converse call to the same model. It needs no internet.
- It is third-party instruction text. Pin one commit, have the session read it in full, and ship it in the bundle
  supplement with its sha256.
- Its README says it leaves numbers, citations and claims as written, and that it is not built to evade
  AI-use detection. The lane does not rely on that statement: section F checks it mechanically.
- The form requires disclosure. `af_he-msca-dn_en.pdf` says applicants "must be transparent in disclosing which
  AI tools were used and how they were utilized", and Part B2 carries "10. Declaration on the use of AI". The
  lane keeps a per-section log of which tool did what, so that section 10 can be written truthfully by a human.

---

## D. Step 0 — prepare the network to take the files

**0.1 Tier 2 sources (public, in the repository).** The repository holds form V5.0 for the 2025 call. The 2026
call uses V6.0 (4 April 2026). Add the 2026 form, the MSCA Work Programme 2026-2027 part and the 2026 Guide for
Applicants, and re-extract the limits. Until then the limits below are those of V5.0, and they are `Assumed` for
2026.

| Rule (V5.0, "Instructions for Drafting Part B") | Value |
|---|---|
| Document 1 (B1) | 34 pages: start page 1, table of contents 1, participating organisations 2, sections 1-3 at most 30. Section 1 starts on page 5. Excess pages are blanked. |
| Body text | at least 11 pt; reference font Times New Roman; single line spacing or more; standard character spacing |
| Page | A4; every margin at least 15 mm, headers and footers excluded |
| Density | 5,000 to 6,000 characters a page, spaces included, as the form's indication |
| Tables | at least 9 pt, legible; not a way round the body size |
| References | footnotes, 8 pt; footnotes count towards the limit |
| Hyperlinks | ignored when they expand the proposal |
| Header and footer | acronym and implementation mode on every page; "Part B - Page X of Y" |
| File | PDF with embedded fonts, at most 10 MB a document |
| Document 2 (B2) | no overall limit; section 8 one page a beneficiary, half a page an associated partner, at least 9 pt |

**0.2 Normalise the inputs on the workstation, offline.** The host has no document converters. One script, run
by the operator in his own shell, turns each `.docx` and `.xlsx` under `private/msca_dn_2026` into text
(Markdown for prose, CSV or JSON for tables) and writes `inputs_manifest.json`: path, role, sha256 of the source,
sha256 of the output, and a `read_only` flag.

| Input | Role | Rule |
|---|---|---|
| `DC_WP/DC drafts 2026.docx` | primary | **read-only**. Inserted as written. Never an output of this lane. |
| `DC_WP/WP drafts 2026.docx` | primary | final, per the checklist. Inserted as written. |
| `Clinical datasets.docx` | primary | source of facts for 1.2 and the 3.2 table |
| `Beneficiary partner information.xlsx`, `Associated partner information.xlsx` | primary | the consortium as it is now; the list of who left and who joined |
| `Deliverables/Deliverables.docx`, `Milestones.docx`, `Risks.docx` | secondary | sources for Tables 3.1b, 3.1c, 3.1e |
| `Deliverables/KPIs.docx` | secondary | unchanged, minus the entries of departed partners |
| `Deliverables/Training_events.docx` | tertiary | source for the training table and 1.3 |
| `check_list.docx` | control | becomes the private master template |

**0.3 The text being revised.** The current text of each sub-section is the 2025 original as V14 imported it.
That import was made on the workstation (V14 W05), so the extracted sub-sections are already under the private
root there. Nothing has to be restored from the snapshot.

**0.4 Packs.** For each row of the master template a deterministic slicer builds one pack: the current
sub-section, the input slices that row names, the ESR sentences it answers, the constraints and the character
budget. Small packs are the main cost control.

**0.5 The host.** Create the host stack again (as R15 and V14 H03), with the same controls. Ship a bundle
supplement: the drafting command, the guards, the pinned rule set, and the packs. Inbound route as V14-OP1.
A new readiness receipt names the model, the authority (A5) and the export rule (A6).

**0.6 Outbound route.** Today the host role cannot write to S3 and has no internet. Add one narrow route: write
access to a single `outbound/` prefix of the deploy bucket, encrypted, each object fetched by the operator with a
sha256 check and then deleted with all versions. It is a template change and needs its own evidence step.

**0.7 Rehearsal.** Run the whole lane once on the sanitised proposal and made-up inputs before any private file
is shipped.

---

## E. Step 1 — the master template

The checklist becomes a table of work items. Each row is one well-scoped piece of Part B. The public version is
below. The private version adds the partner names and the row-level notes of the checklist.

**Modes.** `insert`: place finalised text as written. `minimal`: change named sentences only; the rest stays
byte-equal. `rewrite`: redraft the sub-section inside its budget. `table`: build or refill a table from an input.
`sweep`: deterministic search and report, no model.

| ID | Part B target | Mode | Answers | Private inputs | A human must confirm |
|---|---|---|---|---|---|
| M01 | 1.1 introduction and objectives | minimal | ESR-E-03, E-04, E-05 (framing) | partner sheets, Clinical datasets, KPIs | what "improved since last year" may be claimed |
| M02 | 1.1 individual DC projects | insert | — | DC drafts 2026 (read-only) | nothing; over-length is reported, not cut |
| M03 | 1.2 methodology | **rewrite** | ESR-E-01, E-02, E-03, E-04, E-05; "causality" note of the checklist | WP drafts, DC drafts, Clinical datasets | metric definitions, prospective-validation plan, cohort facts, data-security measures |
| M04 | 1.2 new table: sites, clinical staff, researchers | table | ESR-E-05 | partner sheets | every number in it |
| M05 | 1.3 training programme and training-events table | rewrite | ESR-E-07, E-08 | Training_events, partner sheets | who delivers each entrepreneurship and technology-transfer element, and when |
| M06 | 1.4 supervision | minimal | ESR-E-09 | partner sheets | how supervision quality is measured |
| M07 | 2.1, 2.2 | minimal | consortium change; entrepreneurship emphasis | partner sheets, Training_events | — |
| M08 | 2.3 | minimal | ESR-I-01 | — | the IP protection strategy |
| M09 | 2.4 magnitude of impact | rewrite | ESR-I-02 | KPIs | every baseline and target |
| M10 | 3.1 Table 3.1a work packages | insert | ESR-Q-01 | WP drafts 2026 | that dependencies are now stated |
| M11 | 3.1 Table 3.1b deliverables | table | ESR-Q-02 | Deliverables | the validation means of each deliverable |
| M12 | 3.1 Table 3.1c milestones | table | ESR-Q-03 | Milestones | definitions and months |
| M13 | 3.1 Table 3.1d DC table | table | consortium change | DC drafts, partner sheets | recruiting and awarding entities, months |
| M14 | 3.1 Table 3.1e risks | table | ESR-Q-04 | Risks | each activation threshold |
| M15 | 3.2 participants; new table of clinical infrastructure and datasets | rewrite + table | consortium change; checklist | Clinical datasets, partner sheets | access claims |
| M16 | B1 list of participating organisations; B2 section 8 | table | consortium change | partner sheets | every entry |
| M17 | whole document | sweep | consortium change | list of departed partners | — |
| M18 | B2 section 10, declaration on the use of AI | human | form requirement | the lane's tool log | the whole text |

**Out of scope, as instructed:** the three figures (participant map, WP structure, DC graph). The page budget
still reserves their space.

**Not in the checklist but in the ESR:** ESR-E-06 (gender and diversity in cardiology), ESR-E-09, ESR-I-01. M06
and M08 cover two of them as proposals. The consortium should say whether all three are in scope.

---

## F. Step n+1 — the drafting process

Steps 2 to n are the rows of the master template, in this order: M03, M09, M05, M15, then the tables M04 and
M11 to M14, then the `minimal` rows, then `insert` rows, then M17.

**One row, one pass:**

1. **Pack.** Built by the slicer. Its sha256 is recorded.
2. **Draft.** One Converse call. The instruction: write only this sub-section; use only facts present in the
   pack; where a needed fact is absent, write `[[CONFIRM: what is needed]]` and do not supply a value; for
   `minimal` rows return only the changed paragraphs.
3. **Fact guard (deterministic).** Every number, percentage, month, identifier (KPI, deliverable, milestone,
   task, DC) and partner short name in the draft must occur in the pack. A miss fails the row.
4. **Budget guard (deterministic).** Characters with spaces against the row's budget. The budget of a section is
   its length in the 2025 original, moved only by a recorded decision. Added text is paid for inside the same
   section.
5. **Polish.** One Converse call with the pinned rule set. Then the fact guard again, comparing before and
   after: the sets of numbers, identifiers, names and footnote references must be equal. If they differ, the
   polished text is discarded and the draft stands.
6. **Outputs.** The section text, a change note (what changed, which ESR point, which input), the list of
   `[[CONFIRM]]` items, and counts. Read-only inputs are re-hashed and must be unchanged.

**Rules that keep it reliable.** `insert` and `table` rows that only move finalised content use no model. A
failed or malformed answer is a failure of the row, not something repaired silently. One regeneration a row at
most, with a recorded reason. Responses are checkpointed, so a resume replays and does not redraw.

**Rules that keep it cheap.** Small packs. One draft and one polish per row. The fixed instructions are a cached
prefix. An output cap per row.

**Estimate, to be replaced by a measured preflight:** about 18 rows, of which about 8 call the model twice;
roughly 0.3 to 0.5 million input tokens and 0.1 to 0.2 million output tokens; **about 5 to 15 USD** on Opus 5.5
for one full pass, plus about 0.15 USD an hour for the host. Set a hard cap of 30 USD.

**Layout is checked on the workstation, not on the host.** The host produces text. A human assembles it in the
Word source and exports the PDF. The dry import already measures page count and body point size; extend it to
report the 34-page limit, section 1 starting on page 5, embedded fonts, and any text below the size limits.

**After the draft.**
1. Consortium review of the assembled draft and of every `[[CONFIRM]]` item.
2. Pre-evaluation: import as `--document resubmission_2026` (in-process form, V14-F3), then preflight, assess,
   freeze and audit as runbook section 8, under `msca_dn_2026_default` once its applicability is confirmed, with
   the Sonnet 4.6 assessor pin. No `compare`: there is no 2026 ESR. Scores are advisory.
3. Only then may `DC drafts 2026.docx` change, by its authors.

---

## G. Missing, to be provided

| # | Missing | Needed for | From |
|---|---|---|---|
| 1 | The 2026 form (V6.0), the 2026-2027 work programme part, the 2026 Guide for Applicants | limits and section list; whether 3.1 must carry a Gantt chart | public; into Tier 2 |
| 2 | The editable source of the 2025 Part B | assembly | coordinator |
| 3 | Metric definitions per endpoint for the tasks the checklist marks as still lacking them | M03 | WP leads |
| 4 | Clinical staff and researcher numbers per site | M04 | each site |
| 5 | The prospective-validation plan: sites, design, timing | M03 | clinical partners |
| 6 | Data-security measures for clinical data | M03 (ESR-E-02) | data-holding partners |
| 7 | Baselines and targets for the impact measures | M09 | coordinator |
| 8 | Activation thresholds for risks; validation means for deliverables, if not already in the files | M11, M14 | WP leads |
| 9 | Offline descriptions of the entrepreneurship and incubation programmes the checklist links to, and each provider's commitment | M05 | those partners |
| 10 | Whether ESR-E-06, ESR-E-09 and ESR-I-01 are in scope; whether ESR-Q-01 is closed (it is struck through in the checklist) | E | consortium |
| 11 | What "emphasise retrospectiveness" means: the ESR criticised retrospective-only evaluation | M01 | checklist author |
| 12 | Whether the partner sheets hold personal data, and the consortium's agreement to AI processing | A5 | coordinator |
| 13 | Acronym, implementation mode, duration, number of DCs for 2026 | headers, DC table, milestone checks | coordinator |
| 14 | Who draws the three figures, and how much space they take | page budget | consortium |
| 15 | Opus 5.5 model access and quota in the account | step 0.5 | operator |

---

## H. Schedule and its risk

| Day | Work |
|---|---|
| Sat 14 | Decisions A1 to A7. Requests for G out to the consortium. Session builds the normaliser, slicer, drafting command, guards and outbound route, and rehearses on the sanitised proposal. |
| Sun 15 | Operator normalises and ships the inputs. Host created. Rows run in the order of F. Outputs fetched. |
| Mon 16 | Assembly in Word, layout check, `[[CONFIRM]]` list, draft to the consortium. |

**The risk is step 0, not the drafting.** A new host lane with an outbound route, built and evidenced under the
AWS protocol in one day, is tight. If it slips, cut scope to M03, M05, M09 and M15 first. Any route other than
the private host is a separate operator decision and is not proposed here.
