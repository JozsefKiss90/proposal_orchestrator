# B01 — The host packs `outbound/` and serves the archive once, on loopback

Status: ready
Type: task
Blocked by: None — can start immediately
Lane: Stage B drafting (MSCA-DN 2026 resubmission), export route
Source: operator, in session 2026-11-14 ("build the port-forward tunnel"); decision record
`msca-dn-stage-b-drafting-lane_2026-11-14`, gap G2 (how drafts leave the host)
Estimate: 45–60 minutes with tests

## What to build

One host script, `docs/infrastructure_security/evidence_v2/SB/host/sb_outbound_serve.sh`, sent alone by
`deploy/aws/scripts/host-run.ps1` (Run Command, as root). It does four things, in this order:

1. packs every regular file under `/root/sb/outbound/` into one archive, `/root/sb/export/<PO_ARCHIVE>`;
2. prints the archive's size, sha256 and member count;
3. serves that one file at `http://127.0.0.1:<PO_PORT>/<PO_TOKEN>/<PO_ARCHIVE>` until it has been fetched
   once, or until the window ends;
4. deletes the archive, prints what happened, and ends.

A second script, `sb_smoke_seed.sh`, writes one invented text file of `PO_BYTES` bytes into
`/root/sb/outbound/` for the live smoke (B04). It holds no private text and refuses a non-empty folder.

The Session Manager tunnel itself is the workstation's part (B02). This ticket needs no AWS call.

## Vars (sent by `host-run.ps1 -VarsFile`)

| Name | Rule |
|---|---|
| `PO_TOKEN` | required; 64 hex characters; made by the workstation for one fetch |
| `PO_ARCHIVE` | required; `out-<YYYYMMDD>-<6 hex>.tar.gz`, a neutral name as in V14-OP1 |
| `PO_PORT` | default `8765`; 1024–65535 |
| `PO_WINDOW_SECONDS` | default `300`; 30–900 |
| `PO_MAX_BYTES` | default `20000000` |

`SB_W` and `SB_PY` override `/root/sb` and the interpreter, for the rehearsal only (as `V14_W`, `V14_PY`).

## Decisions

- **Loopback only.** The socket binds `127.0.0.1`, never `0.0.0.0`. The script prints the address read back
  from the bound socket.
- **Single use.** One complete GET of the exact path ends the server. A transfer the client drops does not
  count. Any other path, token or method gets 404 or 405 with no body, is counted, and does not end it.
- **The token is never shown.** It is compared with `hmac.compare_digest`. It is not printed and the server
  logs no request line. `host-run.ps1` records var names only.
- **Only `outbound/` leaves.** A symlink, a non-regular file, a hidden file, a name outside
  `[A-Za-z0-9._/-]`, a `..` segment, an empty folder or a total above `PO_MAX_BYTES` refuses the run.
  Nothing listens after a refusal.
- **The archive is reproducible.** Members sorted, mtime 0, uid and gid 0, mode 600, gzip mtime 0. The same
  folder gives the same sha256.
- **Metadata out only.** Stdout is `key=value` lines: `archive_bytes`, `archive_sha256`, `members`,
  `interpreter`, `listening`, `served`, `bytes_sent`, `refused_requests`, `window_seconds`,
  `archive_deleted`. No member name, no content. The last line is `RESULT=expected` or `RESULT=unexpected`.
- **`RESULT=expected`** only when `served=yes`, `bytes_sent` equals `archive_bytes` and the archive is
  deleted. A window that ends unfetched is `served=no`, `RESULT=unexpected`.
- **Interpreter.** `/opt/msca-dn-anonymisation/python/bin/python3` when present, else `/usr/bin/python3`.
  Standard library only, so the smoke can run before the bundle is installed.
- **Clean exit.** A trap deletes the archive on SIGTERM and on the Run Command timeout. A busy port is
  refused before packing.

## Acceptance criteria

Failing tests first, in `tests/test_stageb_outbound_tunnel.py`. They run the script under `BASH` with `SB_W`
and `SB_PY` set, over invented files, and skip where `BASH` is absent, as the R15 host tests do.

- [x] Both scripts are ASCII, LF, pass `bash -n` and end with a `RESULT=` line.
- [x] Happy path: a GET with the token returns bytes whose sha256 equals `archive_sha256`. Then
      `served=yes`, `RESULT=expected`, the archive is gone and the port is closed.
- [x] A second GET after a served one is refused at the socket.
- [x] A wrong token, a wrong name, `/`, HEAD, POST and PUT each get 404 or 405. The server stays up,
      `refused_requests` counts them, and the right GET still works afterwards.
- [x] A client that closes mid-body does not end the server, and `served` stays `no` until every byte of a
      GET is sent. (`served=yes` means sent, not received: operator decision 2026-11-14, see Comments.)
- [x] Window end without a fetch: `served=no`, `RESULT=unexpected`, archive deleted, exit within the
      window plus 5 seconds.
- [ ] Each refusal ends `RESULT=unexpected` with nothing listening: missing or short token, bad archive
      name, symlink, `..` name, hidden file, empty folder, total above the cap, busy port.
- [x] Two runs over the same folder print the same `archive_sha256`.
- [x] A connection to the machine's non-loopback address is refused (skip where there is none).
- [x] With invented member names and a known token, stdout holds neither, and every line is `key=value`.
- [x] `sb_smoke_seed.sh` writes exactly `PO_BYTES` bytes of invented text and refuses a non-empty folder.

Then:

- [x] The full suite shows no new failure by node id against `plans/overhaul/BASELINE.md`.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/B01-host-serves-the-outbound-archive-once.md   Base: harness_overhaul HEAD
Read first: docs/infrastructure_security/evidence_v2/V14/host/v14_inbound.sh and v14_h09_return.sh (style),
            deploy/aws/scripts/host-run.ps1 (how a script and its vars are sent),
            tests/test_aws_host_run_script.py (static checks, BASH, skips)
New files: evidence_v2/SB/host/sb_outbound_serve.sh, sb_smoke_seed.sh, tests/test_stageb_outbound_tunnel.py
Do not touch: deploy/aws/templates/**, deploy/aws/parameters/**, deploy/offline_bundle.json, host-run.ps1
Skills: tdd
Size: ~150 lines of shell with embedded Python, ~200 lines of tests
Record: none in this ticket (B03 writes the export rule)
```

## Out of scope

- The tunnel and the download (B02). The export rule and the step sheet (B03). The live smoke (B04).
- Inbound transfer. It stays on the V14-OP1 route.
- What the drafting command writes into `outbound/`. This ticket takes the folder as given.
- Any S3, IAM, KMS or endpoint change.

## Comments

- 2026-11-14, implemented in `4d127b95`. Evidence: `tests/test_stageb_outbound_tunnel.py` on Windows under
  Git Bash, 37 passed and 3 skipped, stable over three runs and 40 of 40 runs of the drop test.
  - Ticked: each criterion whose test passed.
  - Open: "Each refusal". Every case passes except the symlink, which skips on Windows (no symlink
    privilege). The FIFO and SIGTERM tests also skip there. All three need a Linux run (WSL or the B04 host).
  - Open: "The full suite". The run before the review fixes showed no new failure (42 failed, all in
    the baseline). The fixes touched only the three new files. It is ticked after the full run that
    B02 makes, which includes these tests.

- 2026-11-14, during B02. The full suite showed no new failure: 42 failed, all in the baseline. That
  box is ticked.
  - Reopened: "A client that closes mid-body". After a reset first connection, the second, full GET was
    itself reset mid-body in 3 of 30 runs on Windows (WinError 10054, about 19 s into the read). The
    server still printed `served=yes`, the full `bytes_sent` and `RESULT=expected`. So `served=yes` can
    be false: `sendall` and `shutdown` succeed once the bytes reach the kernel, not the client. The
    server did not end, which is the criterion's first half; the second half fails.
  - B02's sha256 check catches it on the workstation (file deleted, exit 1). The host record would
    still be wrong. Not yet known whether Linux behaves the same; the B04 host is the first Linux run.
  - Reproduce: the drop test, or a loop of it, 2 of 20 failed. Before B02 it passed 40 of 40.

- 2026-11-14, operator decision: narrow the claim. `served=yes` and `RESULT=expected` mean every byte
  was sent, not received; the workstation's sha256 match (B02 `kept`) proves delivery, and B03's record
  states it. The script header says so. The drop test now accepts a reset on the second read, but
  still requires `served=yes`, `bytes_sent` equal to `archive_bytes` and `RESULT=expected`, and checks
  the sha256 whenever the read completes. The reworded criterion is ticked: 20 of 20 drop-test runs,
  and the Stage B file 53 passed and 3 skipped.
