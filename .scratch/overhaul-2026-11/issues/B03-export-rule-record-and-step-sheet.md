# B03 — The export rule on record, the receipt wording and the step sheet

Status: ready (the operator's wording is filled in at review)
Type: task (records; no code)
Blocked by: None for the draft. B01 and B02 for the final script names and hashes
Lane: Stage B drafting (MSCA-DN 2026 resubmission), export route
Source: operator, in session 2026-11-14; closes the A6 part of gap G2 in
`msca-dn-stage-b-drafting-lane_2026-11-14`
Estimate: 30 minutes

## What to build

Three records. Each holds metadata only: no partner, no person, no number and no passage from the 2026
inputs or the 2025 original.

1. **A decision record,**
   `docs/tier4_orchestration_state/decision_log/msca-dn-stage-b-export-route_2026-11-14.json`.
2. **The export sentence of the Stage B receipt** (`processing_route.export`), between `FILL` markers,
   as P2 was handled at V14.
3. **`docs/infrastructure_security/evidence_v2/SB/STEPS.md` and `RUNLOG.md`,** started with the tunnel's
   steps. Later lane tickets add their own steps to the same sheet.

## What the decision record states

- **The route.** Drafts leave the host as one archive through a Session Manager port-forward session to
  the operator's workstation, served once on the host's loopback address, with a sha256 check on both
  sides (B01, B02). The host gets no internet route and no S3 write. No stack changes.
- **What it sets aside, for this lane only.** V14-OP2 (only metadata leaves the host) and V14-OP8
  (sessions use the default document only). V14-OP4 stands: text is read on the host only in an
  interactive session, never in Run Command output.
- **What may leave.** Only the files the drafting lane writes to `/root/sb/outbound/`. The operator's
  wording says which kinds: for example section drafts, change notes, lists of items to confirm, counts.
  **FILL: operator.**
- **Where it lands.** A private folder outside every checkout and outside any cloud-synced folder.
- **Who may receive the drafts next,** and by which channel. **FILL: operator.**
- **What stays as it was.** Inbound transfer by V14-OP1. Bedrock invocation logging off. No session
  preferences document, so no session logging.
- **Not built.** The S3 `outbound/` route of the reviewed proposal (step 0.6). It would change four base
  stacks.
- **Fallback.** If B04 fails, the declared session export (gzip and base64 in an interactive session,
  sha256 on both sides), as V14-D3 did, declared before the run this time.
- **Known gaps.** The session's content is protected by TLS and is not additionally encrypted with the
  project key. CloudTrail records each `StartSession` with its document name, not what was carried.

`review_state` is `agent_drafted_pending_operator_review` until the operator fills the two `FILL` points.

## What the step sheet holds

Written in the V14 `STEPS.md` style: a PowerShell block, what to expect, what to report.

- **SB-T1. Smoke** (B04): seed an invented file, fetch it, check it.
- **SB-T2. Fetch** (every later export): the `sb_fetch.ps1` line, the PASS conditions, and where the
  evidence file goes (`SB_T2_fetch-<n>.json`).
- **SB-T3. CloudTrail, 15 minutes after a fetch.** The V14 H10b block with a changed PASS rule: every
  `StartSession` is by the operator's role and targets the lane's instance; a fetch shows
  `documentName` `AWS-StartPortForwardingSession`; an interactive session shows it null; the counts
  equal the fetches and sessions the operator made.
- **The "never save" list of V14 part H,** repeated, with one line added: the token of a fetch.

## Acceptance criteria

- [ ] The decision record parses as JSON, follows the field set of the lane's first record, and names
      B01 and B02's scripts by path.
- [ ] It names V14-OP2 and V14-OP8 as set aside for this lane only, and V14-OP4 as standing.
- [ ] The two operator points carry `FILL` markers and no agent-written substitute.
- [ ] `STEPS.md` names only scripts that exist in the tree, and every AWS line carries
      `--profile po-r1 --region eu-north-1`.
- [ ] SB-T3 states its PASS rule as above, and says it runs no earlier than 15 minutes after a fetch.
- [ ] No record holds private content. `tools/evidence_secret_scan.py` and `tools/old_id_guard.py` are
      clean over the `SB` folder.
- [ ] The operator has read the record and filled or struck both `FILL` points before B04 runs.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/B03-export-rule-record-and-step-sheet.md   Base: harness_overhaul HEAD
Read first: docs/tier4_orchestration_state/decision_log/msca-dn-stage-b-drafting-lane_2026-11-14.json,
            evidence_v2/V14/RUNLOG.md (V14-OP1 to OP9, V14-D3), evidence_v2/V14/STEPS.md (part H rules, H10b),
            harness/execution_receipt_template_bedrock_converse.json
New files: the decision record; evidence_v2/SB/STEPS.md; evidence_v2/SB/RUNLOG.md
Do not touch: the V14 records, the first lane record (a successor, never an edit), CLAUDE.md
Size: one JSON record, two short Markdown files
```

## Out of scope

- The processing authority for the 2026 inputs (A5) and the RAISE DN opt-in (A7). They get their own
  records.
- The rest of the lane's step sheet (normalise, packs, drafting, host creation).

## Comments
