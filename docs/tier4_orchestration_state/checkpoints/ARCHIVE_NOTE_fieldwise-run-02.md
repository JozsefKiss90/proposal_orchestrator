# Checkpoint / prior-state preservation note — fieldwise-run-02 → fieldwise-run-03

Date: 2026-09-02 · Authority: operator confirmation of the fieldwise-run-03 enactment
(grilling session 2026-09-02; see
`decision_log/fieldwise-run03-instantiation_2026-09-02.json`).

The fieldwise-run-02 line published **no** `phase8_checkpoint.json`: the operator
deliberately skipped the n08a→n08f rerun after the 2026-08-30 gate_12 fixes (gate_12
left red by choice), so checkpoint publication (n08f) never executed on this line. The
write-once checkpoint guard therefore does not bind and there is no checkpoint file to
archive.

The complete prior Tier 4 state of the fieldwise-run-02 line — all `phase_outputs/`,
`validation_reports/`, and the decision log as of the run-03 branch point — is preserved
in full on branch **`fieldwise-run-02`** at commit **`99f6105`** ("enacting
fieldwise-run-03"). The fieldwise-run-03 rerun overwrites phase outputs on branch
`fieldwise-run-03` only.

Per CLAUDE.md §5 (Tier 4 constraints), no formally validated checkpoint state is
destroyed by the rerun: none existed on this line.
