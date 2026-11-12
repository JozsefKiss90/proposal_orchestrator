# V14 — step sheet

| Field | Value |
|---|---|
| Ticket | V14 (lane H2), runbook `plans/msca_dn_pe09_runbook.md` §4–§6 |
| Bundle | O5: tag `msca-dn-freeze-2026-11-12`, revision `17e32d54` |
| Decisions | `RUNLOG.md`: V14-OP1 to OP8, V14-A1 |
| Rehearsal | `REHEARSAL.md`. Every workstation command below ran there over an invented document |
| Who | The operator runs every step. The agent sees only the lines each step says to report |
| Charges | Part W starts none. Part H starts hourly charges at H03 and needs the operator's go first |

## Names used below

| Name | What it is |
|---|---|
| `F` | `C:\Code\proposal_demo\freeze_bundle`, the freeze worktree at `17e32d54` |
| `R` | The private root: a new folder outside every checkout and outside any cloud-synced folder |
| `O` | The output folder for the archive: outside `R` and outside every checkout |
| `PF` | The workstation preflight folder: outside `R` and outside every checkout |
| `<workspace_rel>` | The `workspace_rel` you declare in the configuration input |
| `<manifest_name>` | The `manifest_name` of the revision you declare in the configuration input |

The original's document id is `MSCA-DN-2025_part_b_as_submitted` and its intake id is `msca-dn-2025-original`, both
fixed by the importer's `official_original` configuration.

## Part W — workstation (no AWS, no charges)

Run every `py -3.10 -m` line from `F` (`Set-Location C:\Code\proposal_demo\freeze_bundle`).

### W01 — the freeze worktree

```
git -C C:\Code\proposal_demo\freeze_bundle rev-parse HEAD
git -C C:\Code\proposal_demo\freeze_bundle status --porcelain
```

Expect `17e32d54f2bd60c1d69d9a1b6caa8688c34f036e`, then no output. **Report:** both.

### W02 — the private root

Create `R`. Put the authenticated PDF under it, for example at
`R\private\msca_dn_original\part_b_as_submitted.pdf`. The configuration's `pdf_rel` names that path later.

### W03 — §4 step 1a: measure the original

```
py -3.10 -m tools.import_external_proposal --document official_original --describe
py -3.10 -m tools.import_external_proposal --environment
py -3.10 -m tools.dry_import_original --pdf <R>\private\msca_dn_original\part_b_as_submitted.pdf --expect-sha256 <hash from the authoritative source> --out <R>\v08_dry_import --submission-id <the proposal number> --call-id <the 2025 call id>
```

Reconcile the worksheet against the PDF and fill in the acceptance record, as
`plans/msca_dn_v08_original_dry_import_procedure.md` says. Then:

```
py -3.10 -m tools.dry_import_original --check-acceptance <R>\v08_dry_import\extraction_fidelity_acceptance.json
```

**Report:** the exit code of each line. Nothing else.

### W04 — §4 step 1b: configure and author the workspace

Copy `tools\original_configuration_template.json` to `R\original_configuration.json` and answer every value. Then:

```
py -3.10 -m tools.author_original_workspace --root <R> --config-input original_configuration.json
```

Here `--config-input` is relative to `R`. **Report:** the exit code.

### W05 — §4 step 1c: import, in-process (V14-F3)

Do not run the runbook's `py -3.10 -m tools.import_external_proposal` form. At the tag it refuses after writing one
file (REHEARSAL.md R2). Run the same code in one module instance:

```
py -3.10 -c "import sys; from tools import import_external_proposal as m; sys.exit(m.main())" --document official_original --config-input <R>\original_configuration.json --repo-root <R>
```

Here `--config-input` is a full path under `R`. Read the measured checks against runbook §4's table yourself.
**Report:** the exit code, and the `findings:` and `unchecked:` counts.

### W06 — pack the inbound archive

```
py -3.10 C:\Code\proposal_demo\proposal_orchestrator\docs\infrastructure_security\evidence_v2\V14\workstation\v14_pack.py --freeze C:\Code\proposal_demo\freeze_bundle --root <R> --config-input original_configuration.json --out-dir <O>
```

It writes the ten supplement files into `R` from the tag, checks each sha256, and refuses if an ESR record is under
`R`. It packs the workspace, the register and the supplement, and no PDF, dry-import record or configuration input
(V14-A1). It prints metadata only. **Report:** every line it prints.

### W07 — the workstation preflight

```
py -3.10 -m harness.commands.blind_assessment preflight --repo-root <R> --document MSCA-DN-2025_part_b_as_submitted --graph-root <R>\<workspace_rel> --profile harness/profiles/msca_dn_2025_historical.json --transport bedrock-converse --no-claims --grounding-scope content_focused --import-manifest <R>\<workspace_rel>\docs\tier4_orchestration_state\dev_graph\imports\<manifest_name> --out-dir <PF>
```

No model call. Read the report yourself, flags included. **Report:** the exit code, the `pack set:` hash, and the
number of flags.

### W08 — the measured cost, and a clean worktree

```
py -3.10 C:\Code\proposal_demo\proposal_orchestrator\docs\infrastructure_security\evidence_v2\V14\workstation\v14_cost.py <PF>\preflight_<hash>_0001.json
git -C C:\Code\proposal_demo\freeze_bundle status --porcelain
```

The cost script prints counts, token totals and USD only. **Report:** its seven lines, and confirm that `status`
prints nothing.

The agent then replaces the cost statement's planned and upper figures with these and asks for the go.

## Part H — host (outline; scripts follow the measured cost)

The scripts for these steps are written after W08, before the go. Each returns key=value metadata only, as at R15.

| Step | What | Settled by |
|---|---|---|
| H01 | Before any charge: budget and credits; the account's `SSM-SessionManagerRunShell` preferences, saving only the logging fields (S3 bucket, CloudWatch log group, streaming), all empty or the document absent | OP4, OP8 |
| H02 | Upload the archive to `bundles/<archive_name>` with SSE-KMS (the R6 key); record its version id | OP1 |
| H03 | **Go recorded first.** Create the host stack (R15 step 06 route) | R11 rule |
| H04 | Fetch, install and verify the bundle (R15 07–09). Fetch the archive; check its sha256; unpack into a private root on the host (mode 700). Check the eight in-bundle supplement files equal the installed app's bytes. Delete every version of the archive object, delete markers included, then show none is left | OP1, OP6 |
| H05 | The readiness receipt (runbook §1.1), with `--expect-profile` the historical profile | runbook §1.1 |
| H06 | Preflight, assess (45 calls), freeze, each with `--repo-root <host private root>`. The checkpoint and provenance stay under that root | OP5, REHEARSAL.md |
| H07 | End of a sitting: stop the instance; next sitting: start it. Stopped cost 0.063916 USD per hour | OP3, D1 |
| H08 | After the freeze: upload the ESR record in its own neutral archive by the same route; sha256 `5c9b9c8e…` checked; versions deleted. Audit, compare, review and diff on the host. You write the dispositions and notes in an interactive session | OP1, OP4 |
| H09 | Return to the repository: metadata, numeric scores and spreads only, through a whitelisting script | OP2 |
| H10 | CloudTrail: the Converse events (as R15 step 15), and the `StartSession` events, which show no document name, so each session used the default document | OP8, DC-26 |
| H11 | At final teardown only: check the volume for credential material (counts only); snapshot the root volume, encrypted; show it is private (no `createVolumePermission`); tag and record the deletion date you give. Then the R15 step 14 teardown | OP7, D1 |

## Open before the go

- **V14-F5.** How the register gets its `fidelity_to_submitted_original` declarations (RUNLOG.md).
- **OP7.** The snapshot's deletion date.
- **The cost.** From W08.
