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

## Findings

- **SB-F1. B04 names two host actions that no script performs.** Emptying `/root/sb/outbound` between the two
  smokes, and the evidence file `SB_T1_after.json` (listening sockets on the port, file counts of `outbound` and
  `export`). B03 writes no code, so `STEPS.md` runs both in an interactive session and the operator reports three
  counts. Open: a follow-up adds a counts-only host script for `SB_T1_after.json`, or the operator accepts the
  reported counts in its place.
- **SB-F2. `served=yes` is not proof of receipt.** On Windows the B01 drop test saw the client reset after the host
  had sent every byte (3 of 30 runs). The operator narrowed the claim (decision record E2). Whether it happens on
  Linux is shown at B04, if at all.
- **SB-F3. B01's symlink, FIFO and SIGTERM refusals have not run.** Their tests skip on Windows. The first run is
  on the Linux host (decision record G5).

## Fetches

| `<n>` | When (UTC) | Bytes | Seconds | Result |
|---|---|---|---|---|
