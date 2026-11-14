# B02 — The workstation fetches the archive through a port-forward session

Status: ready
Type: task
Blocked by: B01 (its script is what the rehearsal serves)
Lane: Stage B drafting (MSCA-DN 2026 resubmission), export route
Source: operator, in session 2026-11-14 ("build the port-forward tunnel")
Estimate: 60–90 minutes with tests

## What to build

One workstation script, `docs/infrastructure_security/evidence_v2/SB/workstation/sb_fetch.ps1`, for
Windows PowerShell 5.1. One call brings one archive from the host to a private folder and checks it:

```
powershell -NoProfile -ExecutionPolicy Bypass -File <sb_fetch.ps1> -AwsProfile po-r1 -Outputs <stack outputs file> -Dest <private folder> -Out <evidence json>
```

Optional: `-HostPort` (default 8765), `-WindowSeconds` (default 300), `-ServeScript` (default B01's script).

## What one call does

1. **Refuses before any AWS call** (exit 2) when: `-Out` exists; `-Dest` is missing, is inside a git work
   tree, or is under this repository; `aws` or `session-manager-plugin` is not on PATH; the outputs file
   holds no `InstanceId`; the serve script is missing.
2. **Makes the fetch's secrets and names:** a 64-hex token from the system random generator, and the
   archive name `out-<YYYYMMDD>-<6 hex>.tar.gz`. It writes a vars file outside the repository with
   `PO_TOKEN`, `PO_ARCHIVE`, `PO_PORT` and `PO_WINDOW_SECONDS`.
3. **Starts the host side:** `host-run.ps1` with B01's script and the vars file, as a child process, with
   a timeout of the window plus 120 seconds.
4. **Opens the tunnel:** picks a free local port, then starts
   `aws ssm start-session --target <InstanceId> --document-name AWS-StartPortForwardingSession`
   with `portNumber` and `localPortNumber`, as a child process. The parameters go through a temporary
   file, as in `host-run.ps1`, because PowerShell 5.1 strips inline quotes. It reads the `SessionId`.
5. **Downloads:** polls `http://127.0.0.1:<local port>/<token>/<archive>` every 2 seconds until it gets
   the file or the window ends. It writes to `<Dest>\<archive>.part` and renames on success.
6. **Checks:** waits for the host script to end, reads `archive_sha256`, `archive_bytes` and `RESULT`
   from its output, and compares them with the local file. On any difference it deletes the local file.
7. **Always cleans up,** in a `finally`: `aws ssm terminate-session`, the whole process tree of the
   session, the vars file, the parameters file and any `.part` file.
8. **Writes `-Out` once,** as JSON, metadata only.

## Decisions

- **Exit codes as `host-run.ps1`:** 0 fetched and equal, 1 anything else after an AWS call, 2 refused before.
- **The token never lands on disk in the repository, in `-Out`, or on the console.** The vars file lives
  in the temp folder and is deleted in the `finally`.
- **`-Out` holds:** archive name, bytes, local and host sha256, `sha256_match`, instance id, command id,
  session id, document name, both ports, start and end UTC, and the host's `key=value` lines. It holds no
  token and no listing of `-Dest`.
- **The file is kept only when** the host says `RESULT=expected` and size and sha256 are equal.
- **No retry of a fetch.** A failed call ends with exit 1. The operator runs it again, with a new token.
- **Dependencies:** PowerShell 5.1, the AWS CLI and the Session Manager plugin. Nothing else. The script
  is ASCII.
- **No test-only branch in the script.** The rehearsal works through shimmed `aws` commands (below).

## Acceptance criteria

Failing tests first, in `tests/test_stageb_outbound_tunnel.py`, where `POWERSHELL` and `BASH` exist (skip
otherwise, as the R15 tests do). They use the `_shims` pattern of `tests/test_aws_host_lifecycle_scripts.py`
with a shimmed `aws`:

- `ssm send-command` runs the sent lines locally under `BASH` with `SB_W` set, so B01's real script serves;
- `ssm get-command-invocation` returns that run's status and stdout;
- `ssm start-session` prints a `SessionId` and relays the local port to the host port on loopback;
- `ssm terminate-session` is recorded.

Tests:

- [ ] The script is ASCII.
- [ ] Each refusal of step 1 exits 2 and the shim records no AWS call.
- [ ] Happy path: the archive is in `-Dest`, its sha256 equals the host's, exit 0. The shim saw one
      `send-command`, one `start-session` naming `AWS-StartPortForwardingSession` with both ports, and one
      `terminate-session`.
- [ ] The token the shim received appears nowhere in `-Out`, in stdout or in stderr.
- [ ] After any ending, the temp folder holds no vars file and no parameters file, and no child process
      of the script is left running.
- [ ] The host refuses (for example an empty `outbound/`): no file in `-Dest`, exit 1, session terminated.
- [ ] The host reports a different sha256 (shim alters the line): the local file is deleted, exit 1,
      `sha256_match` false in `-Out`.
- [ ] The tunnel never carries data (shim relays nothing): exit 1 after the window, no `.part` file left,
      session terminated, the host child ended.
- [ ] `-Out` parses as JSON and carries the fields of the Decisions list.

Then:

- [ ] The full suite shows no new failure by node id against `plans/overhaul/BASELINE.md`.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/B02-workstation-fetches-through-the-tunnel.md   Base: harness_overhaul HEAD + B01
Read first: deploy/aws/scripts/host-run.ps1 (temp parameters file, Aws wrapper, exit codes, PS 5.1 notes),
            tests/test_aws_host_lifecycle_scripts.py (_shims, POWERSHELL, BASH),
            evidence_v2/V14/workstation/v14_pack.py (the checks that keep outputs outside checkouts)
New files: evidence_v2/SB/workstation/sb_fetch.ps1; tests added to tests/test_stageb_outbound_tunnel.py
Do not touch: host-run.ps1, deploy/aws/templates/**, deploy/aws/parameters/**
Skills: tdd
Size: ~160 lines of PowerShell, ~200 lines of tests and shims
Record: none in this ticket (B03 writes the export rule)
```

## Risks the live smoke settles (B04), not this ticket

- Whether the admin role may start `AWS-StartPortForwardingSession`, and whether the installed plugin
  supports it.
- Whether the SSM Agent reaches a server bound to `127.0.0.1`. If it dials `::1` only, B01 gets a
  follow-up that binds both loopback addresses.
- Throughput through the tunnel for a file of realistic size.

## Out of scope

- Inbound transfer, several archives in one call, resume of a partial download.
- Session Manager preferences, session logging or KMS session encryption. None is created.
- Any S3, IAM, KMS or endpoint change.

## Comments
