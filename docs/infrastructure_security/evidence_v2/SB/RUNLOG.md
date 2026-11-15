# SB — run log

| Field | Value |
|---|---|
| Lane | Stage B drafting (MSCA-DN 2026 resubmission). Tickets in `.scratch/overhaul-2026-11/issues/` |
| Decisions | `msca-dn-stage-b-drafting-lane_2026-11-14` (O1 to O5); `msca-dn-stage-b-export-route_2026-11-14` (E1 to E9), both in `docs/tier4_orchestration_state/decision_log/` |
| Kept by | agent (Claude), from the operator's decisions in session. The agent sees no proposal text and no draft |
| Step sheet | `STEPS.md`: P, SB-T1 to SB-T3 (the tunnel). Later lane tickets add their own steps |
| Scripts | `host/sb_outbound_serve.sh` and `host/sb_smoke_seed.sh` (B01), `workstation/sb_fetch.ps1` (B02); hashes in the export-route record |

## Settling

| When | Who | What |
|---|---|---|
| 2026-11-14 | operator | The export route chosen in session: one archive through a Session Manager port-forward session, served once on the host's loopback address, sha256 on both sides. Tickets B01 to B04 |
| 2026-11-14 | agent | B01 committed (`4d127b95`); B02 committed (`8c508e92`, follow-up `5c0e3b47`). Workstation tests only: `tests/test_stageb_outbound_tunnel.py`. No AWS call |
| 2026-11-14 | operator | "Narrow the claim": `served=yes` means sent, not received; the workstation's sha256 proves delivery. Committed `0d8d7a41` (SB-F2) |
| 2026-11-14 | agent | B03: the export-route record drafted (`agent_drafted_pending_operator_review`), `STEPS.md` and this log started. Two `FILL` points await the operator: E5 and E7, and with them the receipt's export sentence (STEPS P2). No AWS call |
| 2026-11-14 | operator | E5 confirmed: every file the lane writes to `outbound`, no narrower list of kinds. E7: the operator only, by the fetch into the private folder; no channel known for anyone else (record G7). Record now `operator_decided`; receipt sentence (STEPS P2) complete |
| 2026-11-14 | operator | SB-OP1 below. The agent adds SB-T0 (create the host, after a preflight) and SB-T4 (stop and start) to `STEPS.md`. No AWS call |
| 2026-11-14 | operator | SB-T0a run. PASS on all three files: account and role as expected; session preferences document absent (`InvalidDocument`); no host stack (`does not exist`, `exit=254`). No charge |
| 2026-11-14 | agent | Fixed before SB-T0b: the three `host-lifecycle.ps1` lines of `STEPS.md` (SB-T0b, SB-T4) held a BEL control byte in place of `\a` in `deploy\aws`, so the path did not exist. No other control byte in the SB records or tickets |
| 2026-11-14 | operator | SB-T0b run. PASS: `path=create`, `7 Add`, `CREATE_COMPLETE`, host `Online`, `RESULT=started`. Create executed 22:48:57Z (start 22:47:37Z); SB-T3 counts from 22:47:37Z. Hourly charges from here |
| 2026-11-14 | operator | SB-T1a stopped: no Session Manager plugin on the workstation (SB-F4) |
| 2026-11-14 | operator | Plugin installed (1.2.896.0). SB-T1a PASS; `SB_T1_bundles-before.json` lists the two freeze-bundle objects |
| 2026-11-14 | operator | SB-T1b seed PASS (`Success`, `seed_bytes=1000000`, `RESULT=expected`, 23:02:59Z). The fetch ran with `-Dest` left as the placeholder `<D>` and failed (SB-F5); record kept as `SB_T1_fetch-failed1.json` |
| 2026-11-14 | agent | SB-F5 fixed in `sb_fetch.ps1`: the preflight runs under `Stop` and refuses on any error. Two new refusal cases (a `-Dest` and an `-Out` with forbidden characters); `tests/test_stageb_outbound_tunnel.py` 55 passed, 3 skipped. New blob sha256 `26a7722a8fa78d7d9d32735372dbef25eebe9740b477c46835c332ccb7de859e` (LF) |
| 2026-11-14 | operator | Second fetch (23:22:39Z) failed: the session did not open (SB-F6). Record kept as `SB_T1_fetch-failed2.json` |
| 2026-11-14 | agent | SB-F6 fixed: `session_error` field; fake `FAKE_TUNNEL_SESSION=refuse` and one new test; tunnel tests 56 passed, 3 skipped. New blob sha256 `94264254b8e4ae8c0dc2a1872e521dff7c95c130b67734a75664def7e03b09e8` (LF) |
| 2026-11-14 | operator | Third fetch PASS (23:39:49Z to 23:40:05Z, 16 s whole-fetch): `kept` true, 3064 bytes, sha256 equal, session ended, host `served=yes` `RESULT=expected`. SB-F6 did not recur; its cause stays unknown |
| 2026-11-14 | operator | SB-T1c PASS: `files=1`, `smoke_sha256` equal to the seed's `seed_sha256` |
| 2026-11-14 | operator | SB-T1e run before SB-T1d: seed refused correctly (`refused=the outbound folder is not empty`, 23:48:08Z), kept as `SB_T1_seed2-refused1.json`. Its fetch (23:49:14Z) opened a session and ended after 12 s with no host lines and no failure (SB-F7), kept as `SB_T1_fetch2-failed1.json` |
| 2026-11-14 | operator | SB-T1d PASS: `smoke.txt` removed in an interactive session, `outbound` count `0` |
| 2026-11-14 | agent | SB-F7: `sb_fetch.ps1` now records an error in its main body as `failure=script error <type> at line <n>` (never the message). No test reproduces the B04 error; tunnel tests 56 passed, 3 skipped. New blob sha256 `3f0b7090f80d58e6dbde8ab5be0a013eda8b96c32ab386df3e146dc3a27b7901` (LF) |
| 2026-11-15 | operator | SB-T1e: seed PASS (`seed_bytes=5000000`, `RESULT=expected`, 00:01:55Z); fetch PASS (00:02:11Z to 00:02:26Z, 15 s whole-fetch): `kept` true, 14709 bytes, sha256 equal, session ended, host `served=yes` `RESULT=expected`. SB-F7 did not recur. SB-T3 no earlier than 00:17:26Z |
| 2026-11-15 | operator | SB-T1c (second) PASS: `files=1`, `smoke_sha256` equal to `SB_T1_seed2.json`. SB-T1g PASS: `Compare-Object` printed nothing |
| 2026-11-15 | operator | SB-T1d/SB-T1f first try ran as `ssm-user` without `sudo -i`: `rm` and both `ls` refused (Permission denied), so the two folder counts are void; `ss` count `0` stands. Rerun as root |

### Operator decisions

- **SB-OP1. Host lifetime.** SB-T0 creates the lane's host for B04. After the smoke it is stopped and kept for the
  drafting lane, which resumes it rather than creating another. Stopped, the stack still costs about 0.064 USD an
  hour (the V14 figure). Teardown is the lane's own step, when the lane ends.

## Findings

- **SB-F1. B04 names two host actions that no script performs.** Emptying `/root/sb/outbound` between the two
  smokes, and the evidence file `SB_T1_after.json` (listening sockets on the port, file counts of `outbound` and
  `export`). B03 writes no code, so `STEPS.md` runs both in an interactive session and the operator reports three
  counts. Open: a follow-up adds a counts-only host script for `SB_T1_after.json`, or the operator accepts the
  reported counts in its place.
- **SB-F2. `served=yes` is not proof of receipt.** On Windows the B01 drop test saw the client reset after the host
  had sent every byte (3 of 30 runs). The operator narrowed the claim (decision record E2). Whether it happens on
  Linux is shown at B04, if at all.
- **SB-F4. The preflight did not check the Session Manager plugin.** SB-T0b created the host (22:48:57Z), then SB-T1a
  found `session-manager-plugin` not on PATH and not installed. `sb_fetch.ps1` refuses without it, so nothing ran
  half-way. SB-T0a now checks the plugin before any charge.
- **SB-F5. `sb_fetch.ps1` did not refuse a `-Dest` with forbidden characters.** Under `$ErrorActionPreference =
  "Continue"`, `Test-Path` threw on `<D>`, which skipped the `if` and its refusal; `$Dest` then came out empty and
  the repository and work-tree checks were skipped too. The script went on to AWS calls: it opened port-forward
  session `…-se7dabq8pp8brzgnfpky34kz9a` (23:03:20Z) and started host-run. An error in the poll then ended the run
  after 5 seconds, which killed host-run, ended the session (`session_terminated` true) and wrote no archive
  anywhere; the token stayed out of the console and the record. Whether the serve Run Command reached the host is
  not recorded (`command_id` null). If it did, its 300-second window ended and it deleted its archive; `smoke.txt`
  stays in `outbound`, and the rerun packs it. SB-T3 will show one more port-forward event than the fetches kept.
  Fixed: the preflight now runs under `Stop` and refuses on any error before an AWS call.
- **SB-F6. A session that did not open left no reason.** The second fetch (23:22:39Z, `-Dest` the private folder)
  ended "the session did not open": no `SessionId` and no "Waiting for connections" within 60 seconds. The host side
  was sound (`listening=127.0.0.1:8765`, `members=1`, `served=no`, `archive_deleted=yes`, `RESULT=unexpected` after
  its 300-second window). The cleanup deleted the session's own output, so the cause is not known; the first fetch's
  session (SB-F5) had opened. Fixed: `sb_fetch.ps1` now keeps the session's last three lines (ASCII, at most 400
  characters) in a `session_error` field and prints them. Record kept as `SB_T1_fetch-failed2.json`.
- **SB-F7. An error in the fetch's main body was recorded as no failure.** `SB_T1_fetch2-failed1.json`: session
  opened, run over in 12 s, `command_id` null, `failure` null; the same shape as SB-F5's run. Inside `try`, a
  statement error ends the body and jumps to the cleanup, which recorded nothing. Not kept, so the cleanup deleted
  any file that came. The error is unknown. Fixed so far as to name it next time: a `catch` records its type and
  line. Not reproduced in a test.
- **SB-F3. B01's symlink, FIFO and SIGTERM refusals have not run.** Their tests skip on Windows. The first run is
  on the Linux host (decision record G5).

## Fetches

| `<n>` | When (UTC) | Bytes | Seconds | Result |
|---|---|---|---|---|
| SB-T1 1 | 2026-11-14T23:39:49Z | 3064 | 16 | kept, sha256 equal |
| SB-T1 2 | 2026-11-15T00:02:11Z | 14709 | 15 | kept, sha256 equal |
