# O5 — re-freeze: step sheet

Handoff `handoff-session-2026-11-11.md` §4, O5. The operator runs every command below in Windows
PowerShell. Nothing here touches AWS. The upload to the deployment bucket belongs to A4 (R15).

## Round 1: suite and lane on `harness_overhaul`

Run from the main tree, on `harness_overhaul` at the commit that adds this file, with a clean
`git status`. Leave the suite file untracked.

```powershell
git status --short; git log --oneline -1
py -3.10 -m pytest -q -rf 2>&1 | Tee-Object -FilePath .scratch\overhaul-2026-11\suite-o5.txt
py -3.10 -m harness.commands.acceptance_lane --junit $HOME\lane-o5.xml; echo "exit=$LASTEXITCODE"
git status --short
```

Pass: the failed node ids equal BASELINE §5 (42 ids), compared by the agent; the lane prints GREEN
with `exit=0`. Any other failure stops O5 until it is fixed and the round re-run.

## Round 2: merge, tag, bundle (only after the agent reports round 1 as PASS)

`<rev>` is the commit round 1 ran on. Downloads and output stay outside both checkouts, under `$HOME\o5`.

```powershell
git switch msca-dn-pre-eval
git merge --no-ff harness_overhaul -m "Freeze: overhaul O1-O3, H1, R11-R14 for V14/V16"
git diff --stat harness_overhaul msca-dn-pre-eval; "diff_lines=$((git diff --stat harness_overhaul msca-dn-pre-eval | Measure-Object -Line).Lines)"
git tag -a msca-dn-freeze-2026-11-12 -m "Re-freeze O5: supersedes msca-dn-freeze-2026-11-11"
git rev-parse msca-dn-freeze-2026-11-12^{commit}
git switch harness_overhaul
git worktree add --detach ..\freeze_bundle msca-dn-freeze-2026-11-12
New-Item -ItemType Directory -Force $HOME\o5\wheels, $HOME\o5\downloads, $HOME\o5\out | Out-Null
cd ..\freeze_bundle
py -3.10 -m pip download --require-hashes -r deploy/requirements-host.txt -d $HOME\o5\wheels --only-binary=:all: --implementation cp --python-version 3.11 --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux_2_28_x86_64
Invoke-WebRequest -Uri ((Get-Content deploy\offline_bundle.json -Raw | ConvertFrom-Json).interpreter.url) -OutFile $HOME\o5\downloads\cpython-3.11.16+20260929-x86_64-unknown-linux-gnu-install_only.tar.gz
py -3.10 -m runner.offline_bundle build --wheels $HOME\o5\wheels --interpreter $HOME\o5\downloads\cpython-3.11.16+20260929-x86_64-unknown-linux-gnu-install_only.tar.gz --out-dir $HOME\o5\out
Get-Content $HOME\o5\out\msca-dn-anonymisation-host.tar.gz.sha256; git -C . rev-parse HEAD; git -C . status --short
cd ..\proposal_orchestrator
```

Pass: `diff_lines=0`; the build prints a sha256 equal to the `.sha256` file; the worktree's HEAD
equals the tag's commit and its status is empty. Paste the output.

## After round 2 (agent)

Decision-log entry `msca-dn-refreeze-o5_2026-11-12.json`: tag, commit, suite and lane evidence,
tarball sha256, superseded tag. Tick O5 in the handoff. From then until V16, nothing is built from
`harness_overhaul`; a run-blocking fix goes on a branch from the tag.
