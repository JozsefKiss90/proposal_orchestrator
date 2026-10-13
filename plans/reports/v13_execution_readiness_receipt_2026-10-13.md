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

The refusals are measured, not reviewed. Every figure below, the mutation runs and the comparison
against HEAD are in
`plans/reports/v13_execution_readiness_receipt_review_2026-10-13.md`.

| Check | Result |
|---|---|
| `tests/harness/test_execution_receipt.py` | 118 passed |
| `tests/harness`, whole directory | 1,843 passed, 17 skipped, no failure |
| The whole suite, in three chunks | 7,160 passed, 37 failed, 86 skipped |
| The 37, measured again at HEAD | every one of them fails at HEAD too |
| `mypy` on both new modules | no error in either file |

No quota was spent. No assessor ran, no runner phase was dispatched, and no scoring was performed.
The frozen 74.60 baseline is untouched. The only command executed outside the suite was the new one,
against a synthetic receipt in a scratch directory.

## 6. One pre-existing defect fixed

The runbook guard's path scan paired backticks over the whole document, and a fenced block opens with
three where the inline-code pattern pairs two. Adding §1.1's command block therefore dropped eight
cited paths from the scan, and only the non-vacuity floor the ticket author had left behind caught
it. The scan now strips the fences first, and the review record carries the detail.

## 7. What the review changed

A standards review and a spec review ran in parallel over the finished change. Ten findings were
acted on and two were declined, and the record of each is a document of its own:
`plans/reports/v13_execution_readiness_receipt_review_2026-10-13.md`.

It is separate because this report ran over the 1,500-word budget, and
`docs/style/internal-docs-profile.md` §5 says an over-budget document is split rather than
compressed. Nothing was dropped in the split. The three changes that bear on what the code does are
the freeze rule keying on the citation, the preflight's emptiness check, and the template's two
pre-answered fields.

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
- The review record was split out on 2026-10-13, which is what brought this report under the
  1,500-word budget. Both parts are linked from each other and neither lost content.
