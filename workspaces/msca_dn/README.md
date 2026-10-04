# MSCA-DN pre-evaluation graph root

This directory is the `--graph-root` of the MSCA-DN pre-evaluation case (`plans/msca_dn_pre_evaluation_spec.md`, §6).
`build_snapshot` resolves its Tier 3 and Tier 4 relative paths against it, so nothing under the
repository's own `docs/` is reachable from here. The demo instance keeps its records there.

What lives here:

- `docs/tier3_project_instantiation/source_materials/sources.json`: the source index, empty until PE-03 writes one source per page.
- `docs/tier4_orchestration_state/dev_graph/intake/msca-dn-2025-sanitised-v1.json`: the ESR intake, whose `call_id` is the
  call the ESR evaluated.
- The baseline's target call belongs to the profile, the run label and the report, never to the intake.
- `docs/tier4_orchestration_state/dev_graph/documents/`, `snapshots/`, `packages/`: empty until PE-03 and PE-06.

What does not live here:

- The two PDFs and the fidelity register, under `docs/tier3_project_instantiation/source_materials/msca_dn/`.
- The ESR record, under `docs/tier4_orchestration_state/msca_dn/esr/`, which no snapshot ever reads.

The assessment artifact under the register is a sanitised derivative of the historical submission.
No result over it is a result over that submission.

Authored by `py -3.10 -m tools.author_msca_dn_workspace`; `--check` exits 1 if any file would change.
