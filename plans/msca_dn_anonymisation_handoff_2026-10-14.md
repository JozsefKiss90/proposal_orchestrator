# MSCA-DN anonymisation pipeline: handoff for ticketing

| Field | Value |
|---|---|
| Date | 2026-10-14 |
| Branch at writing | `msca-dn-pre-eval` at `0f2fa8b` |
| Audience | The agent that turns this document into tickets, then the agents that implement them |
| Status | Handoff. Nothing here is implemented. No private content was read to write it. |
| Authority | Execution aid under `CLAUDE.md` §10.2. Operator decisions are marked as such and stay the operator's. |
| Related | `plans/msca_dn_historical_validation_tickets.md` (V-ledger), `plans/msca_dn_pe09_runbook.md`, `plans/reports/jev_harness_overhaul_assessment_2026-10-13.md`, `docs/tier4_orchestration_state/decision_log/harness-jev-j0-governance_2026-10-14.json`, `docs/infrastructure_security/audit_package/ADR-001-security-decisions.md` |

---

## 1. What this is for

Build a controlled pipeline that turns the submitted 2025 MSCA-DN original into an **anonymised
derivative** that can leave the private AWS network. The derivative must be faithful enough that
assessing it tells us something about the original, and anonymous enough that it may be processed
outside the network (Claude subscription, and Jev once zero data retention is confirmed).

It replaces nothing. The existing sanitised copy (`sanitized_proposal_final.pdf`), its 74.60 frozen
baseline, the ESR record and every approved comparison stay as they are.

### Why a new derivative

The existing sanitised copy was produced ad hoc. Its own fidelity register
(`docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json`) records that
identifiers were generalised, some passages were omitted or rephrased, **all figures were lost, all
citations were removed, the body was reflowed to 12 pt and Table 3.1a was flattened**. A pipeline
that keeps the original's layout, figures, tables and citation structure, and changes only what
identifies people, institutions and the project, should produce a derivative much closer to what
the evaluators read.

### What it unlocks

1. **A dress rehearsal of V14 outside the private network.** The derivative keeps the original's
   page map, work-package tables and appendix mapping, so the V07/V08/V17/V18 import route, preflight,
   checkpointed assessment, freeze and audit can all be exercised end to end before the private run.
2. **A calibrated proxy.** In the same private session as V14, one blind pass over the derivative
   gives a measured original-versus-derivative score delta. Later work on the derivative carries
   that delta.
3. **Data class D3** of the J0 decision: the accepted derivative may go to the Claude subscription,
   and to Jev after zero data retention is confirmed.

---

## 2. Decisions already made

| Decision | Where recorded | Consequence here |
|---|---|---|
| The derivative is data class D3 once accepted; until then it is D4 (private) | J0 decision record, `data_classes` | Every stage before acceptance runs inside the private network |
| "Accepted" means: redaction and rewrite ran inside the private network; the re-identification check found no hit; Table 1.4.1 replaced by a structurally equivalent synthetic table; operator sign-off; export permitted by the private environment's own rule (runbook §10) | J0 decision record, class D3 `condition` | These are the acceptance criteria of the final ticket |
| Table 1.4.1 is **replaced**, not removed | operator, 2026-10-14 session | Removing it would bias the Implementation score; a synthetic table keeps the scoring signal |
| The derivative is a **third document**, distinct from the original and from the sanitised copy | follows from V17 criterion 4 | It needs its own identity, configuration and register; nothing is inherited from the sanitised copy |
| The rehearsal stops at the freeze, with the code revision locked before any ESR comparison of the derivative | operator, 2026-10-14 session | Protects V14's "frozen before ESR" and the no-tuning-toward-85.80 rule |

---

## 3. Constraints every ticket inherits

- **CLAUDE.md** governs: no fabricated facts (§13.3), declared gaps over fabricated completion
  (§15), Confirmed / Inferred / Assumed / Unresolved status vocabulary (§12.2), decisions written to
  Tier 4 (§9.4).
- **The V-ledger's shared constraints** apply unchanged: immutable historical artifacts, successor
  records instead of edits, hashes reproduced and never regenerated, no auto-checked deferral, read
  command help before documenting a command.
- **No private content enters this repository.** Code, schemas, templates, synthetic fixtures and
  metadata-only decision records live here. The original, the entity dictionary, the mapping table,
  the redaction log, unaccepted derivatives and anything quoting them live in the private network
  only. Follow the V17/V18 pattern: what counts as *inside the repository* is measured from the
  module's own location, never taken from an argument, and a private path inside the repository is
  refused.
- **ADR-001 controls stay intact.** The private host has no internet route, admits only Bedrock
  (`anthropic.claude-*`) through PrivateLink, runs with `ORCHESTRATOR_PRODUCTION_MODE=true` (which
  rejects every non-Bedrock backend) and `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata` (no prompt or
  response content written to disk). Bedrock calls are limited to `eu-west-1` and `us-east-1`.
  Software reaches the host only through the offline deployment bundle (Decision 8). None of this
  is relaxed for the pipeline.
- **Import boundary.** `harness → runner` only; `tools/` and `scripts/` never import `harness`.
  Pipeline code that calls Bedrock goes through `runner/transport/bedrock_converse.py`.
- **Cost.** Bedrock calls are metered against the employer-funded account. Every model stage
  enforces a token budget and stops when it is reached.
- **Never a runtime gate.** The pipeline is an authoring tool. It evaluates no DAG gate and writes
  no canonical Tier 5 artifact.

---

## 4. What already exists to build on

| Need | Existing component | Note |
|---|---|---|
| Measure a PDF before import | `runner/dry_import.py` (V08): heading candidates, table inventory, figure inventory, point sizes, character accounting, citation inventory | Run it on the original **and** on each derivative; the comparison is the structural fidelity check |
| "Zero is not proof" | `dry_import.MEASUREMENT_ONLY_BASES`, `check_acceptance` | A figure's presence must be looked at, not inferred from a count; applies equally to the derivative |
| Private configuration and graph root | `runner/original_configuration.py`, `tools/author_original_workspace.py` (V17) | The derivative needs the same route with its own identity |
| Register of a document | `render_register` (derivative) and `render_submitted_register` (original), chosen by `register_of` (V18) | Neither header fits the new derivative as is; see §7 |
| Provenance for the audit | `harness/candidate_provenance.py` (V05) | Must resolve the derivative's identity scope correctly |
| Bedrock inference | `runner/transport/bedrock_converse.py` (native Converse API, IAM credentials, inference profiles) | The only model route on the private host |
| Pre-run evidence | `harness/execution_receipt.py` (V13) | See the blocker in §9 |
| Entity knowledge | the sanitised copy's generalised vocabulary; Tier 3 holds no DN consortium data | The entity dictionary is authored by the operator, privately |

---

## 5. Pipeline

Eight stages. A0 to A7 produce and accept the derivative inside the private network. A8 runs later,
in the V14 session.

```
original (D4) ─► A0 intake ─► A1 policy + entity dictionary ─► A2 deterministic redaction
   ─► A3 bounded model rewrite ─► A4 Table 1.4.1 synthesis ─► A5 re-identification attack
   ─► A6 structural fidelity ─► A7 operator acceptance + export ─► derivative (D3)
                                         └─ any A5/A6 failure loops back to A2/A3
later, in the V14 session:  A8 score fidelity (blind pass on original and derivative, same session)
```

### A0. Source intake

Decide what the pipeline edits. Two options; the operator chooses (open decision O1):

- **Word source** of Part B, if one exists that matches the submitted PDF. Edit the document,
  re-render to PDF with the same template. Layout, figures and tables survive best. Requires a
  check that the source renders to the submitted PDF (page count, headings, tables) before any
  edit, because a source mismatch has bitten this project before.
- **The submitted PDF**, edited in place with PyMuPDF redaction annotations plus inserted
  replacement text. Faithful layout for same-length replacements; longer rewrites overflow and
  must be constrained by A3's length budget.

Either way: pin the input by hash, run `dry_import.measure` on it, and store the inventory
privately as the **reference inventory** for A6.

### A1. Anonymisation policy and entity dictionary

Two artifacts with different homes:

- **The policy** (`anonymisation_policy/1`, public, versioned, hashed): the categories and the rule
  for each. No real entity appears in it. Starting categories, each with *keep*, *generalise* or
  *replace* and a replacement pattern:

  | Category | Default rule | Example replacement pattern |
  |---|---|---|
  | Person names (supervisors, PIs, staff) | replace | `Supervisor S03`, consistent per person |
  | Institutions, departments, companies | replace | `Beneficiary B2 (university, EU Member State)` |
  | Project acronym and title | replace | fixed pseudonym across the document |
  | Cities, regions, countries | generalise | `a Central European capital`; keep EU/associated status where scoring-relevant |
  | Unique facilities and named infrastructure | generalise | `a national high-field NMR facility` (type and scale kept) |
  | Named datasets and cohorts | generalise | `a national longitudinal cohort (n≈…)` (size band kept) |
  | Prior and current grants (ids, acronyms, funders when identifying) | generalise | `a prior ERC Consolidator Grant` |
  | Self-citations and citations of consortium members | replace marker, keep count and position | `[R12]`; reference list entries replaced by neutral placeholders of the same count |
  | Niche topic combinations | flag for A3 and A5, never auto-edit | rewrite only where A5 shows it identifies |
  | Numbers that identify (budgets per partner, staff counts, h-index) | band | `h-index 20–29` |
  | Figures with logos, maps, photos, names | operator review per figure | redraw or mask; never silently drop |

  Scientific content, methods, work-package logic, deliverable and milestone structure, timing and
  effort figures that are not identifying are **kept**.

- **The entity dictionary** (private): every concrete entity in the original, its category and its
  replacement. Seeded by the operator, extended by an NER pass and by A3 proposals the operator
  approves. This dictionary plus the edit log is the **mapping table**. It is D4 forever and never
  leaves the private network.

### A2. Deterministic redaction

Pure code, no model. Apply the dictionary by exact and normalised match (case, diacritics,
hyphenation across line breaks, possessives, initials such as "J. Kiss"), plus regex for DOIs,
grant numbers, ORCID ids, emails, URLs and phone numbers. Write an edit log: span location,
category, dictionary entry id, never the original text outside the private store. The step is
replayable: same input, same policy hash, same dictionary hash, same bytes out.

### A3. Bounded model rewrite

Bedrock through `bedrock_converse.py`, pinned model id, EU inference profile where available.
Scope is narrow on purpose:

- Input is one passage at a time plus the policy, never the whole document.
- Output is a **list of span edits** (start, end, replacement, category, reason), validated against
  the passage, not free prose. An edit outside a flagged category is refused.
- Each edit has a length budget (A0's PDF route makes it tight) and must keep sentence meaning;
  a removal without replacement is refused unless the operator approves it.
- New entities proposed by the model go to the operator for the dictionary; they are not applied
  silently.
- Responses are checkpointed so a failed run resumes rather than redraws, with content stored only
  in the private store (diagnostic level `metadata` stays on for logs).

### A4. Table 1.4.1 synthesis

Replace each supervisor row with a synthetic row that keeps what an evaluator scores:
degree level, career stage band, h-index band, publication-count band, number of PhDs and postdocs
supervised (banded), DN role, and the *kind* of additional expertise. Names, institutions,
publication titles and exact metrics go. Row count and table layout stay identical. The row-by-row
correspondence (real to synthetic) is part of the mapping table. Search the rest of the document
for the same supervisors (WP leads, secondment hosts, recruitment and training sections) and apply
the same pseudonym consistently.

### A5. Re-identification attack

The acceptance test for anonymity. Two independent parts:

- **Deterministic leak scan**: every dictionary entry, every normalised variant, every regex class
  from A2 run over the derivative's extracted text, including headers, footers, figure text layers,
  PDF metadata (author, title, producer, XMP) and embedded file names. Any hit fails.
- **Model attack**: a separate Bedrock call, with a different prompt and preferably a different
  model from A3 so the rewriter does not grade itself. Closed book (no tools, no retrieval). It is
  asked to name the coordinating institution, any partner, any supervisor, the country set, the
  project acronym and the research group, with a confidence and the passage that gave it away.
  A correct guess, scored privately against the dictionary, fails the passage back to A3. Wrong or
  abstained guesses pass. Report counts per category; the passages stay private.

Record the limit honestly: a closed-book attack by a model is not a motivated human expert in the
field. The operator's own read in A7 is the last line.

### A6. Structural fidelity

Run `dry_import.measure` on the derivative and compare with the A0 reference inventory: page count,
heading markers and their pages, table inventory, figure inventory, body point size, citation
marker count and positions. Differences are findings, each one either explained by the policy
(for example a masked logo) or fixed. "Zero is not proof" applies: a figure counted present is
looked at, not just counted.

### A7. Operator acceptance and export

The operator reads the derivative, reviews the A5 and A6 reports, and signs an acceptance record.
Two records come out:

- **Private**: the full acceptance with the mapping table hash, the edit log hash and the
  re-identification details.
- **Public** (`docs/tier4_orchestration_state/decision_log/`): metadata only. Derivative hash,
  policy version and hash, pipeline code revision, A5 and A6 counts by category, model ids, the
  operator's signature, and the rule of the private environment that permits the export. This is
  the record the J0 D3 condition points to.

Export uses the private environment's own path (the S3 gateway under the deployment role, per
ADR-001 Decision 7 and the operational procedure). The export procedure is written down, not
improvised.

### A8. Score fidelity (in the V14 session, after A7)

Not an acceptance condition for D3, but required before any score on the derivative is read as
informative about the original. In the V14 private session, after the original's blind run is
frozen, run one blind pass over the derivative with the same profile, model and sample plan, and
freeze it. Record the per-criterion and total deltas as a successor record. Report the delta as a
single measurement with the within-assessor spread beside it, never as a correction factor; the V14
rule against carrying a delta forward as a predictor applies here too. No ESR material is involved
in this step.

---

## 6. Records and schemas

| Record | Home | Notes |
|---|---|---|
| `anonymisation_policy/1` | repository | versioned, hashed; a change re-opens acceptance |
| entity dictionary | private | D4 |
| redaction and rewrite edit log | private | D4; byte-replayable for A2 |
| mapping table (dictionary + edit log + Table 1.4.1 row map) | private, KMS-encrypted store | D4 forever |
| reference inventory and derivative inventory | private (they quote headings) | counts may be copied into the public record |
| `reidentification_report/1` | private; counts copied to the public record | |
| derivative document configuration (V17-style) | private, then exported with the derivative | own identity; nothing inherited from the sanitised copy |
| derivative fidelity register | exported with the derivative | see §7 |
| acceptance record | public (metadata) + private (full) | the D3 trigger |
| score-fidelity record | public, metadata only | A8 |

---

## 7. Identity and register

The derivative is neither the submitted text nor the sanitised copy. Concretely:

- It needs a **document identity** of its own and a configuration completed through the V17 route
  but from its own measurement. `complete_from_input` already refuses to redeclare the sanitised
  copy, which is the right behaviour.
- Its **fidelity register** should state its own facts: derived from the authenticated original by
  pipeline revision X under policy Y; layout preserved or reflowed (from A6); figures preserved,
  masked or redrawn (counts); citations replaced by neutral markers with counts preserved; Table
  1.4.1 synthetic. Today `render_register` carries the sanitised copy's header and
  `render_submitted_register` the original's. A third renderer, or a parameterised derivative header
  chosen by `register_of`, is required, and neither existing renderer may render it.
- `harness/candidate_provenance.py` must resolve the derivative's identity scope as a derivative of
  the original, so the integrity audit words its findings correctly.

---

## 8. Testing approach

- All code is tested here on **synthetic Part B fixtures** (the V17 pattern: build a non-sensitive
  Part B shape in a temporary directory outside the repository). The fixture needs planted
  entities in every A1 category, a supervisor table shaped like 1.4.1, a figure with a text layer
  and a logo image, PDF metadata carrying a name, hyphenated names across line breaks, and a niche
  topic combination.
- A2 replay is asserted byte-equal. A5's leak scan is asserted to catch every planted entity, and
  a mutation run (disable one normalisation) must fail it.
- Model stages run against a fake backend in tests. A live Bedrock smoke run on the synthetic
  fixture, inside the private network, is part of the deployment ticket, not the unit tests.
- **Optional pilot (open decision O5):** run the pipeline on the FIELDWISE MSCA-PF proposal, locally,
  before touching the DN. FIELDWISE's original has already been processed through the subscription,
  so this needs no private network; it does need the fellow's agreement because her CV is the most
  personal part. It tests the method (re-identification rate, layout preservation, score delta)
  against a document whose original and evaluation are both at hand.

---

## 9. Gap found while writing this: the harness cannot build a Bedrock backend

This affects V14 and A8 directly, and it should become its own ticket ahead of the rehearsal. It is
a wiring gap, not a policy conflict. The harness uses `claude-cli` locally because the Max
subscription is reachable only through the CLI; on AWS the API is the natural route, and nothing in
the hardening needs to change.

What the code does today:

- The assessor's `openai-compatible` transport builds its backend through `resolve_provider_config()`
  and `build_openai_backend()` (`harness/judge.py`, `_get_backend`). That function always builds an
  HTTP OpenAI-style client and requires a `base_url`.
- With `bedrock_converse`, the route the private host uses (`runner/transport/bedrock_converse.py`,
  the deployment guide's smoke test), there is no `base_url`, so the build raises.
- The other Bedrock preset, `bedrock`, targets the `bedrock-mantle.{region}.api.aws` proxy, which is
  not the `bedrock-runtime` VPC endpoint and is unreachable from a host with no internet route.
- The freeze's `TRANSPORT_ISOLATION_EVIDENCE` (`harness/blind_baseline.py`) knows only `claude-cli`
  and `openai-compatible`, and the V13 receipt assumes a CLI version and argv.

The fix:

1. `judge._get_backend` builds `BedrockConverseBackend` when the resolved backend is
   `bedrock_converse`, passing the pinned model, temperature and token limit.
2. `blind_assessment` gains a `bedrock-converse` transport choice, and the freeze gains its isolation
   entry. A Converse call carries no tools and no filesystem, so the claim is simpler than the CLI's.
3. The V13 receipt reads the transport actually used. Converse does send `temperature` and
   `maxTokens` (`inferenceConfig`), unlike the CLI, so its settings table differs.
4. The judge-independence rule is re-checked: on AWS the drafter and the assessor would share a
   provider, where locally they differ.

It touches the blind lane's transport, so it needs operator approval and tests at the level V13 set.

---

## 10. Suggested ticket slicing

The ticketing agent may re-slice, but should keep the dependencies and the exit conditions.

| Id | Ticket | Depends on | Exit condition |
|---|---|---|---|
| AN0 | Operator decisions O1–O6 recorded | none | decision record in Tier 4 |
| AN1 | Bedrock Converse backend for the harness assessor, freeze isolation entry, receipt generalisation (§9) | operator approval | synthetic blind pass over the Bedrock backend freezes under V04 with a validated receipt; lane green |
| AN2 | `anonymisation_policy/1` schema, loader, hashing, the starting policy | AN0 | policy loads, hash recorded, no real entity in it (asserted) |
| AN3 | Synthetic Part B fixture with planted entities (§8) | none | fixture builds outside the repo; every category planted |
| AN4 | A0 intake: source pin, render check (Word route) or in-place edit harness (PDF route), reference inventory | AN0 (O1), AN3 | fixture intake reproduces its inventory |
| AN5 | A2 deterministic redaction with normalisation and edit log | AN2, AN3 | every planted direct identifier removed; byte-equal replay |
| AN6 | A3 bounded rewrite: span-edit schema, validator, length budget, checkpoint, fake backend | AN5 | refusal cases tested; resumes from checkpoint |
| AN7 | A4 Table 1.4.1 synthesis and cross-document pseudonym consistency | AN5 | row count and layout identical; bands match source bands |
| AN8 | A5 leak scan (text, metadata, figure layers) and model attack | AN6, AN7 | every planted entity caught; mutation fails it; attack report schema |
| AN9 | A6 structural fidelity comparison over two dry-import inventories | AN4 | differences reported per category; figures require looked-at status |
| AN10 | Derivative identity, configuration and register (§7); provenance in the audit | AN9 | neither existing renderer renders the derivative; audit words its scope as derivative |
| AN11 | A7 acceptance records (private and public) and the written export procedure | AN8, AN9, AN10 | public record holds no private content (asserted) |
| AN12 | Offline bundle update and private-host smoke run on the synthetic fixture | AN1, AN11 | bundle installs on the host; pipeline and assessor both run against Bedrock |
| AN13 | Operator run on the DN original; acceptance | AN12 | signed acceptance record; derivative exported as D3 |
| AN14 | Dress rehearsal outside the network on the derivative, stopping at the freeze | AN13 | import, preflight, assess, resume, freeze, audit all pass; revision locked |
| AN15 | A8 score fidelity, inside the V14 session | AN14, V14 | successor delta record |
| AN-P | Optional FIELDWISE pilot | AN11, O5 | re-identification and fidelity reported for FIELDWISE |

---

## 11. Open decisions for the operator

| Id | Question | Default if not decided |
|---|---|---|
| O1 | Edit the Word source or the submitted PDF? | Word source if one renders to the submitted PDF; otherwise PDF |
| O2 | Which Bedrock model for A3, and which (different) one for A5? | the pinned assessor model for A3; a different Claude family member for A5 |
| O3 | Re-identification threshold: zero correct guesses per category, or a tolerance? | zero, for institutions, people and the acronym; country set may be guessed if the policy keeps it |
| O4 | Which locations are kept at country level, given that MSCA scoring reads the network's geography? | generalise below country; keep EU / associated / third-country status |
| O5 | Run the FIELDWISE pilot first? | no, unless the fellow agrees |
| O6 | Approve the harness Bedrock Converse backend (§9) as a change to the blind lane's transport | required before V14 regardless of this pipeline |

---

## 12. Out of scope

- Any change to the existing sanitised copy, its 74.60 baseline, or the approved comparisons.
- Any ESR comparison of the derivative before the V14 revision is locked.
- Sending anything to Jev; that follows the J0 data classes and the zero-data-retention record.
- The Stage B 2026 candidate (V16). The same pipeline may serve it later; it is not ticketed here.
