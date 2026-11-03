# 04 — One content-hash module: one canonical rule, two named formats

Status: needs-triage
Type: task
Blocked by: None — can start immediately
Source: `discovery/architecture-review-harness-2026-11-03.html`, candidate E. Not grilled; written on
operator request 2026-11-03, with recommendations taken as decisions.
Findings: F6 (groundwork for 05/06)

> `needs-triage` until the Step 3 scope cut admits it; then `ready-for-agent`.

## What to build

Every harness hash is computed by one module, and the two stored formats are named rather than
implied. Today:

- the canonical-JSON hash rule is written three times (pre-evaluation profile, regression fingerprints,
  rubric fingerprint);
- the file hash is written three times (record binding, evidence preflight, blind baseline);
- records hold two formats with nothing saying which is which: `sha256:`-prefixed for canonical
  content hashes (candidate hash, profile version, rubric fingerprint), bare hex for file hashes
  (`report_sha256`, `comparison_sha256`, …).

The format leaks to callers. The shared numbered-path helper only works with a prefixed hash (it splits
on `:`), and display code slices candidate hashes at 19 characters but file hashes at 12.

After this ticket, callers ask for a **content hash** (a parsed value, canonical JSON, prefixed) or a
**file hash** (raw bytes, bare hex), and use one **short form** for names and display that accepts either.

## Decisions (operator accepted recommendations, 2026-11-03)

- **No format change, no re-stamping.** Every hash the harness writes today keeps exactly its current
  bytes. Frozen baselines, reports, checkpoints and E4 fingerprints written before this ticket stay valid.
- **Three operations:**
  - content hash of a value: canonical JSON with sorted keys, compact separators, UTF-8, non-ASCII
    kept, `sha256:` prefix;
  - file hash of bytes or a path: bare hex;
  - short form of either for names and display (12 hex characters).
  The regression fingerprint, which today stores the canonical hash *without* a prefix, keeps doing so
  through an explicit unprefixed call.
- **Set hashes keep their own field selection.** The gold-set hash and the materiality-set hash choose
  which fields count, and that choice stays theirs. They use the module only for the digest primitive,
  and their output bytes are unchanged.
- **Numbering accepts both formats.** The shared numbered-path helper and the two remaining private
  copies (operator-review Markdown pair, response checkpoint) use the short form, so a bare-hex digest
  no longer crashes them. The two copies are folded into the shared helper.
- **Separate from `runner/fingerprints.py`.** Gate freshness is the runtime's concern, and the one-way
  import rule means the runner never depends on harness code. This ticket does not touch the runner.

## Acceptance criteria

Characterisation first (written before anything moves, all must stay green):

- [ ] On fixtures, the candidate hash, profile version, rubric fingerprint, rubric-set fingerprint, regression section fingerprint, gold-set hash, materiality-set hash, evidence-preflight pack-set hash and blind-baseline report hash are byte-identical before and after.
- [ ] An existing frozen blind baseline and an existing E4 fingerprint fixture still load and verify.

Failing tests first:

- [ ] The numbered-path helper accepts a bare-hex digest and yields the same name as for the prefixed form of the same digest.
- [ ] The short form of a prefixed and of a bare digest of the same bytes is identical.

Then:

- [ ] No harness module outside the hash module calls `hashlib.sha256` or builds canonical JSON for hashing (a boundary test pins this; the response checkpoint's per-response hash may use the file-hash operation).
- [ ] Display code uses the short form; no hard-coded slice lengths for hashes remain in the DN record modules.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [ ] **PE-09 acceptance lane green** (admission rule 5: evidence-preflight and blind-assessment code change).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/04-one-content-hash-module.md   Base commit: <sha at start>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md, plans/overhaul/BASELINE.md
Seam: a new hash module in harness/ — callers switch from local helpers; no stored format changes
Do not touch: runner/fingerprints.py, any frozen record on disk, the set-hash field selections,
      §17 call graph, Tier 1–3 docs
Tests first: characterisation (byte-identical hashes), then the two numbering/short-form failing tests
Size: ~150–250 changed non-test lines, mostly deletions and call-site swaps
```
