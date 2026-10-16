# Export procedure: the accepted anonymised derivative (A7)

Stage A7 of `plans/msca_dn_anonymisation_handoff_2026-10-14.md`, ticket AN11 of
`.scratch/msca-dn-anonymisation/tickets.md`. This procedure moves an accepted derivative out of the
private network as data class D3. The operator runs it in AN13. Nothing here is improvised on the
day: a step not written below is not part of the export.

The procedure adds no runtime gate and changes no ADR-001 control. It uses the one egress path the
private host already has, the S3 gateway endpoint, under the deployment role.

## Before the first step

The derivative is D4 until it is accepted. Acceptance is the record
`runner/anonymisation_acceptance.py` writes. It refuses unless the A5 leak scan passed with no hit,
the A5 model attack passed with no correct guess, A6 explained every difference, A4 replaced Table
1.4.1 and the operator attested every read. It writes two records into the acceptance directory:

- `acceptance.json`, the private record. It stays in the private network.
- `public_acceptance.json`, the public record. It holds hashes, counts, model ids, the operator's
  signature and the export rule. It is the record the J0 D3 condition points to.

## Steps

| Step | Action | Rule that permits it |
|---|---|---|
| 1 | On the host, confirm that the acceptance directory holds both records, and that the public record's `derivative.sha256` is the hash of the derivative to export. | The J0 D3 condition: a derivative leaves only once accepted, and the acceptance is its own decision record (`docs/tier4_orchestration_state/decision_log/harness-jev-j0-governance_2026-10-14.json`). |
| 2 | Confirm that the rule named in the public record's `export_rule` is one of the approved environment's rules and permits this export. Stop if it does not. | Runbook §10: the approved environment's own rules decide what leaves (`plans/msca_dn_pe09_runbook.md`). |
| 3 | Copy `public_acceptance.json` alone to `s3://proposal-orchestrator-deploy-232538551827/deliverables/anonymised_derivative/<public record id>/` with `aws s3 cp`, under the host's `ec2-ssm-role`, and download it on the workstation. It holds hashes, counts, ids and dates only. | Runbook §10 lets the public workspace hold hashes, counts, dates and decision ids (`plans/msca_dn_pe09_runbook.md`). The route is the S3 gateway exception of ADR-001 Decision 7 (`docs/infrastructure_security/audit_package/ADR-001-security-decisions.md`). |
| 4 | Commit `public_acceptance.json` to `docs/tier4_orchestration_state/decision_log/` as `<public record id>.json`, unchanged. The derivative is D3 from this commit, and not before. | CLAUDE.md §9.4: a decision that affects future interpretation is written to the decision log (`CLAUDE.md`). The J0 D3 condition names this record (`docs/tier4_orchestration_state/decision_log/harness-jev-j0-governance_2026-10-14.json`). |
| 5 | Assemble the export set in a new directory on the host. It holds exactly three files: the derivative PDF, its V17 configuration input and its fidelity register. Write a manifest of each file's name and sha256. | Handoff §6 names the configuration and the register as exported with the derivative (`plans/msca_dn_anonymisation_handoff_2026-10-14.md`). |
| 6 | Check the set against the list under "What never leaves" below. Any other file in the set stops the export. | The J0 record's D4 members (`docs/tier4_orchestration_state/decision_log/harness-jev-j0-governance_2026-10-14.json`) and handoff §3 (`plans/msca_dn_anonymisation_handoff_2026-10-14.md`). |
| 7 | Archive the set and copy it to the same S3 prefix with `aws s3 cp`, under the host's `ec2-ssm-role`. The copy goes through the S3 gateway endpoint. | ADR-001 Decision 7, the S3 gateway exception, which names `ec2-ssm-role` as the role for S3 operations (`docs/infrastructure_security/audit_package/ADR-001-security-decisions.md`), and the archive route of operational procedure §3.6 (`docs/infrastructure_security/audit_package/operational_procedure.md`). |
| 8 | On the workstation, download the archive with `aws s3 cp`, unpack it, and check every file's sha256 against the manifest and the derivative's against the committed public record. A mismatch stops the export. | Operational procedure §3.6 (`docs/infrastructure_security/audit_package/operational_procedure.md`). Runbook §10 lets the public workspace hold hashes (`plans/msca_dn_pe09_runbook.md`). |

## What never leaves

None of these is in the export set, and none is copied to the bucket:

- the original and anything quoting it;
- the entity dictionary;
- the mapping table: the dictionary, every edit log and the Table 1.4.1 row map;
- the A0 reference inventory and the derivative inventory, which quote headings;
- the A3 rewrite plan, its checkpoints and its entity proposals;
- the leak scan report, the re-identification report and the re-identification details;
- the A6 report and the figure review;
- the private acceptance record.

The public record carries the counts of the reports by category. That is all of A5 and A6 that
leaves.

## Unresolved before AN13

These are open, and the export does not run until each is settled and recorded:

- **The write grant for `deliverables/`.** The deployment guide records a policy for `ec2-ssm-role`
  that grants S3 read on the deploy bucket and write to `evidence/` only. Operational procedure §3.6
  writes to `deliverables/`, and no recorded grant covers that prefix. Status: Unresolved. AN12
  confirms the grant on the host, or the operator records a different prefix here.
- **The private environment's export rule.** This repository does not hold it (runbook §10). The
  public record carries the rule the operator names, declared Assumed. Status: Unresolved until the
  operator names it in AN13.
- **The mapping table's store.** The handoff puts the mapping table in a KMS-encrypted store. No
  stage writes it there yet; the A4 row map sits beside the derivative (AN7). Status: Unresolved,
  for AN12.
- **The bucket copy's retention.** No recorded rule says how long the archive stays in the bucket
  after step 8. Status: Unresolved; the operator settles it under the approved environment's rules
  in step 2.
