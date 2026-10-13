# V13 completion report — the private execution readiness receipt and its validator

| Field | Value |
|---|---|
| Date | 2026-10-13 |
| Branch | `msca-dn-pre-eval` |
| Ticket | V13, gate G5 |
| Closes | The evidence half of finding F04, which closes F04 with V12 |
| Decision record | `docs/tier4_orchestration_state/decision_log/msca-dn-execution-receipt_2026-10-13.json` |
| Status | Agent-drafted. Acceptance is the operator's. |

## 1. What was missing

The subscription assessor's controls are real. The tool list is empty and rendered as `--tools ""`
rather than omitted, `--strict-mcp-config` strips the operator's MCP servers, and the child runs in a
fresh directory outside every clone. Each has a test that would fail if it broke.

None of that is runtime evidence about a private run, and none of it is authorisation.

What this repository can read after a private run is the report's own declarations: a model pin, a
version tag, a transport name. Each is a string the run was told to record. A pin does not evidence
that the named model answered. A version tag does not evidence which CLI build was on the private
machine. A transport name does not evidence that the environment permitted the proposal text to be
sent at all.

So the operator had to verify four things before a run, with nothing to verify them against:

- which `claude` executable and which version will answer;
- which configured settings actually reach it;
- which directory the child runs in, and that this is not a sandbox;
- which rule of the private environment permits the processing, and what may leave.

V12 recorded all four as the operator's own record and said this runbook does not stand in for it.
That is the evidence half of F04.

## 2. What was built

A receipt schema, a reader that refuses an incomplete one, a validator that reads it against the
intended Stage A pair, a command, and a template.

| Artifact | What it is |
|---|---|
| `harness/execution_receipt.py` | The schema, the reader and the validator |
| `harness/commands/execution_receipt.py` | The command the operator runs privately |
| `harness/execution_receipt_template.json` | The form to fill in, refused as a receipt |
| `tests/harness/test_execution_receipt.py` | 118 cases over a synthetic receipt |
| `plans/msca_dn_pe09_runbook.md` §1.1 | The command, what it refuses, what it reports |

The receipt covers eight sections, one per question the ticket names:

| Section | What it holds |
|---|---|
| `processing_route` | The rule that permits the processing, what may be sent, what may leave |
| `cli_version` | The resolved executable and what `claude --version` printed |
| `model_identity` | The pin, and `attested: false` beside it |
| `effective_settings` | Each setting, its value, whether the transport sends it, and the evidence |
| `rendered_invocation` | The argv as handed to the operating system |
| `isolation_check` | The verified directory, the sandbox answer, and the evidence |
| `checkpoint` | Where the run will write it, and that nothing is there yet |
| `preflight` | The report the run is bound to, pinned by its bytes |

## 3. What the reader refuses outright

Exit 2, before any comparison runs.

| Refusal | Why |
|---|---|
| A receipt inside this repository | It holds private paths and the operator's verification acts |
| An unfilled `<placeholder>` | A template is not evidence |
| A missing section, a missing field, an empty field | An absent answer is not a negative answer |
| A transport the settings table does not cover | The reader cannot say what reached a transport it has no table for |
| A wrong schema, unreadable bytes, no file | Fail-closed |

The repository-root rule is measured, the way the subscription judge measures its own working
directory. The committed template is refused on that rule, and refused again on its placeholders if
it is copied out of the tree. Each protection has its own case.

## 4. What the validator reports

Exit 1. Nineteen findings, each named rather than summarised. The five that carry the ticket's
substance:

**A setting claimed transmitted that the transport does not send.** `TRANSPORT_SETTINGS` is read off
`runner/claude_transport.py`. The pinned temperature of 0 reaches no provider, because the CLI takes
no temperature argument. The judge's token limit is handed to `invoke_claude_text` and never rendered
either: the child's ceiling is the transport's own `CLAUDE_CODE_MAX_OUTPUT_TOKENS` value. The other
direction is reported too, because a receipt understating what leaves is as wrong as one overstating
it.

**A claimed operating-system sandbox.** There is none. The child runs from a directory with the
operator's own privileges, filesystem rights and network access.

**A freeze condition or a freeze record cited as the isolation evidence.** The freeze reads what a
report declares about its invocation. Verifying that invocation is the receipt's own act, and the two
are separate records. The reader holds the freeze's own `BASELINE_CHECKS` tuple, so this finding
cannot go stale against a renamed condition.

**A candidate or profile other than the intended pair.** The candidate is named on the command line,
because the original's document id is private. The profile is pinned by the bytes in this tree, and
the private clone sits at the revision the decision log names.

**A preflight that is not the one the receipt records.** The receipt's preflight block copies figures
the report already carries. The validator reads that report back instead: its bytes against the
recorded hash, then its record type, candidate, profile, profile version, pack-set hash, import
manifest and grounding scope. A preflight naming no import manifest is incomplete, and so is one
that realised no pack or no criterion input. The manifest is named explicitly, and the resolver's
predecessor default is never relied on.

An `insufficient_context` pack is not incompleteness. The pack set records it as an explicit
outcome, and refusing it here would refuse a declared result.

Those five paragraphs name nine of the nineteen fields. The other ten:

- a setting the receipt does not cover at all;
- an argv without the empty tool list, or without `--strict-mcp-config`;
- a non-empty tool list;
- two working directories that disagree;
- a working directory not declared outside every clone;
- a working directory inside the clone;
- a checkpoint that already exists;
- a checkpoint outside the clone;
- a version string not read from the CLI;
- a pin marked attested, or one that does not name the transport.

## 5. Verification

The refusals are measured, not reviewed. `tests/harness/test_execution_receipt.py` builds a receipt
and a preflight report in a temporary directory, then removes or alters one thing per case. The cases
cover eight missing sections, an empty string, a placeholder, every finding, the three command exit
codes, and the committed template.

The missing-field sweep is generated from the synthetic receipt rather than hand-listed. Every field
of every section is removed in turn, so a field added to the schema and not to the reader fails here.

Two mutation runs confirm the module is not vacuous. The first made four changes — tolerating a
transmitted temperature, dropping the sandbox refusal, dropping the placeholder rule, and skipping
the preflight hash comparison — and failed seven checks. The second made three, over the rules added
after review, and failed nine. The module was restored from a copy each time.

| Check | Result |
|---|---|
| `tests/harness/test_execution_receipt.py` | 118 passed |
| `tests/test_msca_dn_pe09_runbook.py` | 19 passed |
| `tests/harness/test_acceptance_lane.py` | 68 passed |
| `tests/harness/test_profile.py` | 23 passed, so neither new module names an instrument |
| `tests/harness/test_boundary.py` | 19 passed, so the import boundary holds |
| `mypy` on both new modules | no error in either file |
| `tests/harness`, whole directory | 1,843 passed, 17 skipped, no failure |
| The rest of the lane | 1,080 passed |

The whole suite ran in three chunks, because a single run was killed twice for host memory. Together:
7,160 passed, 37 failed, 86 skipped.

None of the 37 is this ticket's. They were measured again at HEAD in a throwaway worktree carrying
this tree's `.env`. The `tests/runner` failing set is identical, node id for node id. The other chunk
fails 18 where HEAD fails 23, and all 18 are in HEAD's set. No test fails here that passes at HEAD.
The five that fail only at HEAD read gitignored run artifacts a fresh worktree does not carry.

No quota was spent. No assessor ran, no runner phase was dispatched, and no scoring was performed.
The frozen 74.60 baseline is untouched. The only command executed outside the suite was the new one,
against a synthetic receipt in a scratch directory.

## 6. One pre-existing defect fixed

The runbook guard's path scan paired backticks over the whole document. A fenced block opens with
three backticks, and the inline-code pattern can pair only two of them, so each fenced block left one
over and shifted the pairing of every inline span after it.

Adding §1.1's command block therefore dropped eight cited paths from the scan. The scan had found
twelve; it found five. Nothing failed except the non-vacuity floor the ticket author had put there,
which is what caught it.

The scan now removes the fenced blocks before reading inline code, and reads the command lines
separately, where a path is an argument rather than a backticked token. Both floors are asserted, and
removing the fence-stripping fails the test.

## 7. What the review changed

A standards review and a spec review ran in parallel over the finished change. Nine findings were
acted on.

| Finding | What changed |
|---|---|
| The report said "fourteen findings" where nine were narrated and ten remained | Section 4 counts them, and the two it had omitted are listed |
| The template pre-answered `review_state` and `declared_status` | Both are placeholders now, and a test asserts neither is a valid value |
| `_discover_profile` was a verbatim copy of the sibling command's `_discover` | `historical_profile.discover_declarations` is shared by both commands |
| `TRANSPORT_ISOLATION_EVIDENCE` was imported and unused | Removed. The test still binds both transport maps to it |
| A loop raised the same message `_section` raises | Removed. `effective_settings` has its own presence check |
| `validate` and `render` against the siblings' `check` and Markdown `render` | `check` and `summary_lines` |
| `.get(transport, ())` on a transport `load_receipt` had already refused | Indexed, and the test binds both maps to the same keys |
| The freeze rule substring-scanned condition names over prose | It keys on citing the freeze, so `assessor_transport` in honest evidence is not a finding |
| "A complete preflight" checked identifiers only | A report that realised no pack or criterion input is incomplete |
| `written_by` was optional | Required. Who verified these things is evidence |

Two were declined. The runbook listed a mismatched binding under refusals while the code reports it:
the doc was wrong, and §1.1 now puts it under findings at exit 1. The profile identifier, path, hash
and version travelling together is a data clump, but `PreflightBinding` mirrors the receipt's JSON
keys one for one, which is this repository's shape for a parsed declaration.

## 8. What this is not evidence of

- That PE-09 has been executed. It has not, here or anywhere this repository can see.
- That the private environment permits any content to leave it. The receipt records which rule
  permits the processing. It does not grant it, and §10 of the runbook states none of those rules.
- That a validated receipt makes a run blind. The receipt records the controls and the verification;
  the controls themselves are the transport's, with their own tests.
- That G5 is closed. The code for it exists, and closing the gate is the operator's.
- That V13 is accepted. Acceptance is the operator's.

## 9. Open

- The receipt is validated where its preflight report is, because the validator reads that report.
  Running the command from this public workspace against a private receipt is refused on the
  repository-root rule, which is the intended order: the command belongs in the private clone.
- The real receipt does not exist. It is the operator's, produced privately, and V14 is where it is
  produced.
- `review_state` and `declared_status` are the operator's own declarations on their own receipt. The
  reader checks that each is one of the repository's values, and cannot check that the declaration is
  true.
- This report is 1,903 words against the 1,500-word validation-report budget in
  `docs/style/internal-docs-profile.md` §5, which says an over-budget document is split rather than
  compressed. The overage is section 7, the review record. Splitting it out is the smallest fix, and
  the decision is the operator's.
