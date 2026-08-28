# Checkpoint / prior-state preservation note — fieldwise-run-01 → fieldwise-run-02

Date: 2026-08-28 · Authority: operator ruling Q7 of
`decision_log/fieldwise-run-02-baseline_2026-08-28.json`

The fieldwise-run-01 line published **no** `phase8_checkpoint.json` (this directory was
empty at the branch point), so the write-once checkpoint guard does not bind and there is
no checkpoint file to archive.

The complete prior Tier 4 state of the ELTE-hosted run — all `phase_outputs/` (phases 1–8,
gate results under run ids up to and including the consolidated Phase 8 run `845413cf`),
`reuse/`, `validation_reports/` and the decision log as of the host switch — is preserved
in full on branch **`fieldwise-run-01`** at commit **`22b13bf`** ("preparing host
switch"). The fieldwise-run-02 rerun overwrites phase outputs on this branch only.

Per CLAUDE.md §5 (Tier 4 constraints), no formally validated checkpoint state is
destroyed by the rerun: none existed on this line.
