# B04 — Operator: live smoke of the tunnel, on an invented file

Status: ready (B01 to B03 done; SB-T0 creates the host)
Type: operator step (the agent checks the evidence files afterwards)
Blocked by: B01, B02, B03, and a running host stack (the lane's host-creation step)
Lane: Stage B drafting (MSCA-DN 2026 resubmission), export route
Source: operator, in session 2026-11-14
Estimate: 20 minutes at the terminal, plus the CloudTrail check 15 minutes later

## Purpose

Prove the route on the real host before any private draft exists. Three things cannot be shown on the
workstation: that the admin role may start a port-forward session, that the SSM Agent reaches a server
bound to `127.0.0.1`, and how fast the tunnel is.

## Execution boundary

The operator runs every step. No private file is on the host yet. The smoke file is invented text made
on the host by `sb_smoke_seed.sh`. Hourly charges are already running, because the host stack exists.

## Steps (written out in `evidence_v2/SB/STEPS.md`, SB-T1 and SB-T3)

1. `session-manager-plugin --version` on the workstation. **Report:** the version.
2. Seed: `host-run.ps1` with `sb_smoke_seed.sh` and `PO_BYTES=1000000`. Out: `SB_T1_seed.json`.
3. Fetch: `sb_fetch.ps1` with `-Dest` a private folder outside every checkout. Out: `SB_T1_fetch.json`.
4. Repeat 2 and 3 with `PO_BYTES=5000000`, after emptying the host folder. Out: `SB_T1_seed2.json`,
   `SB_T1_fetch2.json`.
5. Host state after the fetches: one Run Command that prints the listening sockets on the port and the
   file counts of `/root/sb/outbound` and `/root/sb/export`. Out: `SB_T1_after.json`.
6. Deploy bucket unchanged: list `bundles/` and compare with the listing made before the smoke.
7. Fifteen minutes later, SB-T3 (CloudTrail). Out: `SB_T3_start-session.json`.
8. Delete the two fetched smoke archives from the private folder.

## PASS

- [ ] Both fetches: exit 0, `sha256_match` true, `served=yes`, `RESULT=expected`,
      `listening=127.0.0.1:<port>`, `refused_requests=0`.
- [ ] `SB_T1_after.json`: nothing listens on the port, and `/root/sb/export` is empty.
- [ ] The bucket listing is unchanged.
- [ ] SB-T3: two `StartSession` events with `documentName` `AWS-StartPortForwardingSession`, by the
      operator's role, on the lane's instance, with no error. No such event by any other caller.
- [ ] The seconds each fetch took are recorded in `RUNLOG.md`, so the lane knows what a real export costs
      in time.
- [ ] No evidence file holds the token. The agent checks each file by script.

## If it fails

- **`start-session` is refused or the plugin is too old:** report the error line. The fix is on the
  workstation or in the operator's role, not on the host.
- **The tunnel opens but the download never starts:** report `SB_T1_fetch.json`. The likely cause is the
  loopback address family, and B01 gets a follow-up that binds both `127.0.0.1` and `::1`.
- **Two failed attempts after a fix:** stop. Record the failure in `RUNLOG.md` and use the fallback named
  in B03's record for the first drafting run.

## Out of scope

- Any private file. The first private export is a later lane step, after this ticket passes.
- Changing a stack, a policy or the session preferences.

## Comments

- 2026-11-14, operator, in session (SB-OP1): the host is created for this ticket by `STEPS.md` SB-T0, and after
  the smoke it is stopped (SB-T4) and kept for the drafting lane. Order: SB-T0a, SB-T0b, SB-T1a to SB-T1i, then
  SB-T3 15 minutes after the second fetch. Step 5's `SB_T1_after.json` is read by hand for now (RUNLOG SB-F1).
