# Tickets: MSCA-DN anonymisation pipeline

These tickets build a controlled pipeline that turns the submitted 2025 MSCA-DN original into an anonymised derivative. The accepted derivative becomes data class D3 and may leave the private network. Source: `plans/msca_dn_anonymisation_handoff_2026-10-14.md` (the handoff). Ticket ids follow its §10 table.

Work the **frontier**: any ticket whose blockers are all done. AN0 and AN3 can start immediately. Clear context between tickets.

Constraints that apply to every ticket:

- `CLAUDE.md` governs. No fabricated facts, declared gaps over fabricated completion, the §12.2 status vocabulary, and durable decisions in Tier 4.
- The V-ledger's shared constraints apply unchanged. Historical artifacts are immutable, corrections are successor records, and hashes are reproduced, never regenerated.
- No private content enters this repository. The original, the entity dictionary, the mapping table, edit logs, inventories that quote headings and unaccepted derivatives stay in the private network. Follow the V17/V18 pattern: the repository boundary is measured from the module's own location, and a private path inside the repository is refused.
- ADR-001 controls stay intact: no internet route, Bedrock only through PrivateLink, production mode on, diagnostic level `metadata`, regions `eu-west-1` and `us-east-1`, software only through the offline bundle.
- Import boundary: harness imports runner only. Tools and scripts never import the harness. Every Bedrock call goes through the runner's Bedrock Converse transport.
- Every model stage enforces a token budget and stops when it is reached.
- The pipeline is an authoring tool. It evaluates no DAG gate and writes no canonical Tier 5 artifact.
- Tests run with `py -3.10` on synthetic fixtures built outside the repository. Model stages use a fake backend in tests.
- Out of scope: the existing sanitised copy and its 74.60 baseline, any ESR comparison of the derivative before the V14 revision is locked, anything sent to Jev, and the Stage B 2026 candidate.

## AN0 — Record operator decisions O1 to O6 (DONE 2026-10-14)

**What to build:** The operator answers the handoff's open decisions, and a Tier 4 decision record holds the answers. O1 picks the edit route: the Word source or the submitted PDF. O2 picks the rewrite model and a different attack model. O3 sets the re-identification threshold. O4 sets which locations stay at country level. O5 decides the FIELDWISE pilot. O6 approves the Bedrock Converse backend as a change to the blind lane's transport. Any decision left open records the handoff's default and says so.

**Blocked by:** None. Can start immediately.

- [x] A decision record in the Tier 4 decision log answers O1 to O6, each marked as an operator answer or as an adopted default.
- [x] The record contains no private content.
- [x] O6 is recorded as approved before any AN1 ticket starts.

## AN3 — Synthetic Part B fixture with planted entities (DONE 2026-10-14)

**What to build:** A non-sensitive Part B fixture, built in a temporary directory outside the repository, that every later ticket tests against. It plants an entity in every policy category. It carries a supervisor table shaped like Table 1.4.1, a figure with a text layer and a logo image, PDF metadata holding a name, names hyphenated across line breaks, self-citations, identifying grant numbers and a niche topic combination. A manifest of the planted entities lets tests check what was found.

**Blocked by:** None. Can start immediately.

- [x] The fixture builds outside the repository, and building it twice gives identical bytes.
- [x] Every policy category has at least one planted entity, listed in the planted-entity manifest.
- [x] The dry-import measurement of the fixture lists the supervisor table, both figures, the metadata and the citation markers.

## AN1a — Bedrock Converse backend for the blind assessor (DONE 2026-10-14)

**What to build:** The assessor can run a blind pass through Bedrock Converse, the only model route on the private host. Today the judge always builds an OpenAI-style HTTP client and requires a base URL, so a `bedrock_converse` configuration raises. The judge builds the Converse backend instead, passing the pinned model, temperature and token limit. Blind assessment gains a `bedrock-converse` transport choice. The `bedrock` preset that targets the mantle proxy is not used, because the private host cannot reach it.

**Blocked by:** AN0 (O6 approved).

- [x] A resolved `bedrock_converse` configuration builds the Converse backend with the pinned model, temperature and token limit.
- [x] `blind_assessment` accepts `bedrock-converse` and runs a full synthetic blind pass against a fake Converse backend.
- [x] The existing `claude-cli` and `openai-compatible` routes behave exactly as before, shown by their existing tests.

## AN1b — Freeze isolation evidence and a transport-aware receipt for Converse (DONE 2026-10-15)

**What to build:** A blind pass run over Bedrock Converse can be frozen and carries a valid V13 receipt. The freeze's transport isolation evidence gains a `bedrock-converse` entry. A Converse call carries no tools and no filesystem, so its isolation claim is simpler than the CLI's. The V13 receipt reads the transport actually used, not a CLI version and argv. Its settings table records the `temperature` and `maxTokens` that Converse sends.

**Blocked by:** AN1a.

- [x] A synthetic blind pass over the fake Converse backend freezes under the V04 checks.
- [x] The freeze records the Converse isolation evidence, and a report claiming a transport with no entry is refused.
- [x] The V13 validator accepts a receipt for the Converse pass and refuses one whose recorded transport differs from the report's.
- [x] The PE-09 acceptance lane stays green, and the V12 runbook guard passes on any documented command that changed.

## AN1c — Judge independence when drafter and assessor share Bedrock (DONE 2026-10-15, rule pending operator confirmation)

**What to build:** The grader/generator independence rule still holds on AWS, where the drafter and the assessor would share a provider. Locally they differ, so the rule has never been tested in this configuration. The guard compares the resolved assessor model with the drafter model and refuses a match. The decision on whether a shared provider with different models is admissible is written to Tier 4.

**Blocked by:** AN1a.

- [x] The independence guard refuses a Converse configuration whose model equals the drafter model.
- [x] A Converse configuration with a different Claude model passes the guard, shown by a test.
- [x] A Tier 4 decision record states the rule for a shared provider and the reason.

## AN2 — The anonymisation policy (DONE 2026-10-15)

**What to build:** A public, versioned and hashed `anonymisation_policy/1`. It lists each category with its rule (keep, generalise or replace) and a replacement pattern, as in the handoff's §5 A1 table. The starting policy applies O3 and O4. A loader validates the policy and returns its hash. Any change to the policy re-opens acceptance.

**Blocked by:** AN0 (O3 and O4).

- [x] The policy schema validates, the loader refuses a malformed policy, and the hash is stable across loads.
- [x] The starting policy covers every category in the handoff's table, including figures needing operator review per figure.
- [x] The policy's category ids are the fixture's `CATEGORIES` ids (set by AN3), shown by a test.
- [x] A test asserts that the policy names no real entity.

## AN4 — Source intake (A0) (DONE 2026-10-15)

**What to build:** The pipeline pins its input and records the reference inventory for later comparison. The route follows O1. On the Word route, a render check proves the source renders to the submitted PDF before any edit: page count, headings and tables. On the PDF route, an edit harness applies redaction annotations and inserts replacement text, refusing a replacement that overflows its length budget. Either way, the input is pinned by hash and its dry-import measurement is stored privately as the reference inventory.

**Blocked by:** AN0 (O1), AN3.

- [x] Intake on the fixture pins it by hash and reproduces the fixture's own inventory.
- [x] Word route: a source that does not render to the pinned PDF is refused. PDF route: an overflowing replacement is refused.
- [x] The reference inventory is written only to a private path, and a path inside the repository is refused.

## AN5 — Deterministic redaction (A2) (DONE 2026-10-15)

**What to build:** Pure code, with no model, that applies the entity dictionary to the document through AN4's edit route. Matching is exact and normalised: case, diacritics, hyphenation across line breaks, possessives and initials such as "J. Kiss". Regex classes catch DOIs, grant numbers, ORCID ids, emails, URLs and phone numbers. PDF metadata (author, title, producer, XMP) and embedded file names are scrubbed under the policy. The edit log records span location, category and dictionary entry id, never the original text.

**Blocked by:** AN2, AN3, AN4.

- [x] Every planted direct identifier in the fixture is removed or replaced, including those in the metadata.
- [x] Same input, same policy hash and same dictionary hash give byte-equal output.
- [x] The edit log contains no original text, asserted by a test.

## AN8a — Deterministic leak scan (first half of A5) (DONE 2026-10-15, review rule confirmed by the operator)

**What to build:** A scan of the derivative for anything the dictionary or the A2 regex classes would match. It covers extracted body text, headers, footers, figure text layers, PDF metadata including XMP, and embedded file names. Any hit fails the derivative. The scan is also the first independent check of A2.

**Blocked by:** AN5.

- [x] The scan catches every planted entity in the unredacted fixture and finds none in the redacted fixture.
- [x] A mutation run that disables one normalisation makes the scan fail on the redacted fixture.
- [x] Hits are reported by location and category, with no private text in the report.

## AN6 — Bounded model rewrite (A3) (DONE 2026-10-15, rules pending operator confirmation)

**What to build:** A Bedrock rewrite for what A2 cannot handle, such as niche topic combinations. The input is one passage at a time plus the policy, never the whole document. The output is a list of span edits (start, end, replacement, category, reason), validated against the passage. New entities the model proposes go to an operator queue for the dictionary and are not applied. Responses are checkpointed in the private store, so a failed run resumes rather than redraws.

**Blocked by:** AN5.

- [x] The validator refuses an edit outside a flagged category, an edit over its length budget, and a removal without replacement unless the operator approved it.
- [x] A proposed new entity lands in the operator queue and changes no text.
- [x] A run interrupted mid-document resumes from its checkpoint without new model calls for completed passages.
- [x] The token budget stops the stage when reached.

## AN7 — Table 1.4.1 synthesis (A4) (DONE 2026-10-15, rules pending operator confirmation)

**What to build:** Table 1.4.1 is replaced by a structurally equivalent synthetic table, not removed, because removal would bias the Implementation score. Each supervisor row keeps what an evaluator scores in banded form: degree level, career stage, h-index, publication count, PhDs and postdocs supervised, DN role and kind of additional expertise. Names, institutions, publication titles and exact metrics go. The same pseudonym appears wherever that supervisor appears elsewhere in the document.

**Blocked by:** AN5.

- [x] On the fixture, the synthetic table has the same row count and layout as the source table.
- [x] Every band contains the source value it replaces.
- [x] Each fixture supervisor carries one pseudonym across the whole document.
- [x] The real-to-synthetic row map is written only to the private store.

## AN8b — Closed-book model attack (second half of A5) (DONE 2026-10-15, rules pending operator confirmation; cannot run until the research-group threshold is set)

**What to build:** A separate Bedrock call tries to re-identify the derivative. It uses a different prompt and the O2 attack model, so the rewriter does not grade itself. It runs closed book, with no tools and no retrieval. It names the coordinating institution, any partner, any supervisor, the country set, the acronym and the research group, each with a confidence and the passage that gave it away. Guesses are scored privately against the dictionary under the O3 threshold. A correct guess sends that passage back to A3.

**Blocked by:** AN6, AN7, AN8a.

- [x] A `reidentification_report/1` schema records counts per category, with passages kept private.
- [x] Against a fake backend, a correct guess fails its passage back to A3, and wrong or abstained guesses pass.
- [x] The attack refuses to run with the same model as A3.
- [x] The report states its limit: a closed-book model is not a motivated human expert.

## AN9 — Structural fidelity comparison (A6) (DONE 2026-10-16)

**What to build:** A comparison of the derivative's dry-import inventory with the A0 reference inventory. It covers page count, heading markers and their pages, tables, figures, body point size, and citation marker count and positions. Each difference is either explained by the policy, such as a masked logo, or reported as a finding to fix. "Zero is not proof" applies: a figure counted present is not accepted until it has been looked at.

**Blocked by:** AN4, AN5.

- [x] Comparing the fixture with its redacted derivative reports differences per category.
- [x] A difference the policy does not explain is a finding, not a pass.
- [x] A figure whose only basis is a measurement is refused as preserved, consistent with the V08 acceptance check.

## AN10 — The derivative's identity, configuration and register (DONE 2026-10-16, rules pending operator confirmation)

**What to build:** The derivative is a third document, distinct from the original and the sanitised copy, and nothing is inherited from the sanitised copy. It gets its own document identity and a configuration completed through the V17 route from its own measurement. A third register renderer, chosen by `register_of`, states the derivative's facts. These are: the pipeline revision and policy version it came from, layout preserved or reflowed, figure counts, neutral citation markers with counts kept, and a synthetic Table 1.4.1. Candidate provenance resolves the derivative's scope, so the integrity audit words its findings as a derivative of the original.

**Blocked by:** AN9.

- [x] Configuration completion refuses to redeclare the sanitised copy, as it does today, and accepts the derivative's own identity.
- [x] Neither existing register renderer renders the derivative, and the new renderer renders nothing else.
- [x] The integrity audit on a fixture derivative words its scope as a derivative of the original.

## AN11 — Acceptance records and the written export procedure (A7) (DONE 2026-10-16, rules pending operator confirmation)

**What to build:** The operator acceptance step produces two records. The private record holds the full acceptance, the mapping table hash, the edit log hash and the re-identification details. The public Tier 4 record holds metadata only. It records the derivative hash, the policy version and hash, the pipeline revision, A5 and A6 counts by category, the model ids, the operator's signature and the private environment's rule that permits export. This public record is the one the J0 D3 condition points to. The export procedure through the S3 gateway, under the deployment role per ADR-001 Decision 7, is written down.

**Blocked by:** AN8b, AN9, AN10.

- [x] A test asserts that the public record contains no private content.
- [x] The public record refuses to build unless the leak scan and attack both passed and the fidelity findings are all explained.
- [x] The written export procedure names each step and the rule that permits it.

## AN12 — Offline bundle and private-host smoke run (CODE DONE 2026-10-16, rules confirmed, host steps pending operator)

**What to build:** The pipeline and the Converse assessor reach the private host through the offline deployment bundle (Decision 8). On the host, the full pipeline runs on the synthetic fixture against live Bedrock, and a blind pass runs over the Converse backend. The operator performs the host steps.

**Blocked by:** AN1b, AN1c, AN11.

- [ ] The updated bundle installs on the private host without an internet route.
- [ ] The pipeline runs A0 to A7 on the synthetic fixture against live Bedrock within its token budgets.
- [ ] A synthetic blind pass over Converse freezes on the host with a validated receipt.

Code: `runner/offline_bundle.py` (bundle with a CPython 3.11 interpreter, operator decision D1), `tools/anonymisation_host_smoke.py`, `harness/commands/converse_smoke.py`. Procedure: `plans/msca_dn_an12_host_runbook.md`. Decision record: `msca-dn-an12-offline-bundle_2026-10-16`. The three criteria stay open until the operator runs the host steps. Operator decisions D2 to D4 (2026-10-16): the audit amendment `plans/msca_dn_an12_audit_amendment_draft.md` is approved and applied (2026-10-16); an A7 refusal over A3 edits satisfies criterion 2; `verify` measures the private endpoint and leaves a DNS-failed probe unmeasured.

## AN12a — Apply the A3 rewrite plan (A3b)

**What to build:** A stage applies the validated span edits of an A3 rewrite plan to the A2 output through the stage edit harness (`apply_stage_edits`), as A4 does. It writes a new derivative and an edit log in the private store. A5, A6 and A7 then read the applied derivative. Queued entity proposals stay out: they go to the dictionary, and A2 reruns. Without this stage, any A3 edit makes A7 refuse (AN11 R3), so the DN original cannot reach acceptance.

**Blocked by:** AN12 code (operator decision D3, 2026-10-16).

- [ ] On the fixture, every validated A3 edit lands at its span, and the edit log binds the plan, input and output hashes.
- [ ] An edit that no longer matches its passage is refused, and no text changes.
- [ ] A7 accepts a derivative whose A3 edits were applied, and still refuses a plan with a queued entity proposal.

## AN13 — Operator run on the DN original and acceptance

**What to build:** The operator authors the entity dictionary privately and runs the pipeline on the DN original inside the private network. They read the derivative, review the A5 and A6 reports and sign the acceptance. The derivative is exported as D3 through the written procedure.

**Blocked by:** AN12, AN12a.

- [ ] A signed private acceptance record and its public metadata record exist.
- [ ] The derivative is exported through the written procedure and lands outside the network as D3.

## AN14 — Dress rehearsal outside the network, stopping at the freeze

**What to build:** The V14 route runs end to end on the derivative outside the private network: V07/V08/V17/V18 import, preflight, checkpointed assessment, resume, freeze and audit. The rehearsal stops at the freeze. The code revision is locked before any ESR comparison of the derivative, protecting V14's "frozen before ESR" and the no-tuning-toward-85.80 rule.

**Blocked by:** AN13.

- [ ] Import, preflight, assess, resume, freeze and audit all pass on the derivative.
- [ ] The locked code revision is recorded in Tier 4 before any ESR material is read.

## AN15 — Score fidelity (A8), inside the V14 session

**What to build:** In the V14 private session, after the original's blind run is frozen, one blind pass runs over the derivative with the same profile, model and sample plan. It is frozen. The per-criterion and total deltas are recorded as a successor record with the within-assessor spread beside them. The delta is a single measurement, never a correction factor. No ESR material is involved.

**Blocked by:** AN14, V14.

- [ ] The derivative's pass is frozen under the same profile, model and sample plan as the original's.
- [ ] A public metadata-only successor record holds the deltas and the within-assessor spread.
- [ ] The record states that the delta is not a predictor.

## AN-P — Optional FIELDWISE pilot

**What to build:** The pipeline runs locally on the FIELDWISE MSCA-PF proposal to test the method before the DN. FIELDWISE's original and evaluation are both at hand, so the pilot can measure re-identification rate, layout preservation and score delta.

**Blocked by:** AN11, and AN0 recording O5 as "yes" with the fellow's agreement.

- [ ] The fellow's agreement is recorded before any run.
- [ ] Re-identification and structural fidelity results are reported for FIELDWISE.
