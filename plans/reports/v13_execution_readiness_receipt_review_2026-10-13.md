# V13 review and verification record

| Field | Value |
|---|---|
| Date | 2026-10-13 |
| Branch | `msca-dn-pre-eval` |
| Ticket | V13, gate G5 |
| Parent report | `plans/reports/v13_execution_readiness_receipt_2026-10-13.md` |
| Holds | The review record, the measurements, and the pre-existing defect the ticket fixed |
| Why separate | The parent ran 1,903 words against a 1,500-word budget. `docs/style/internal-docs-profile.md` §5 says an over-budget document is split rather than compressed, so this is the split. Nothing was dropped: sections 5 to 7 of the parent moved here, and the parent keeps the headline figures and a pointer. |
| Status | Agent-drafted. Acceptance is the operator's. |

## What the review changed

A standards review and a spec review ran in parallel over the finished change. Ten findings were
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

## The measurements

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

## One pre-existing defect fixed

The runbook guard's path scan paired backticks over the whole document. A fenced block opens with
three backticks, and the inline-code pattern can pair only two of them, so each fenced block left one
over and shifted the pairing of every inline span after it.

Adding §1.1's command block therefore dropped eight cited paths from the scan. The scan had found
twelve; it found five. Nothing failed except the non-vacuity floor the ticket author had put there,
which is what caught it.

The scan now removes the fenced blocks before reading inline code, and reads the command lines
separately, where a path is an argument rather than a backticked token. Both floors are asserted, and
removing the fence-stripping fails the test.

## The two review axes, for the record

The standards review read the change against this repository's documented conventions. Module
docstrings that state a constitutional standing, refusals that name the field, no module-level
mutable state, and naming that matches the sibling modules a reader will have open. The spec review
read it against V13's five acceptance criteria and the ticket's verification clause.

Both reviews ran over the finished change rather than over a plan, so every finding above is about
code that existed. The mutation runs recorded in the parent report's section 5 were re-run after the
review's changes landed. That is why there are two of them: four changes failing seven checks before,
and three changes over the new rules failing nine after.
