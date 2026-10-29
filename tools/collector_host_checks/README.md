# Host checks of the R12a evidence collector

Fixed scripts that `tools/collect_evidence_v2.py` sends to the host with SSM Run Command
(`AWS-RunShellScript`), preceded only by `export PO_…=<value>` lines built from the stack outputs,
the parameter files and `deploy/aws/collector_inputs.json`. Decision record:
`aws-redeployment-r12a-collector_2026-10-28`.

Rules every script keeps (tested by `tests/tools/test_collect_evidence_v2.py`):

- No account, Region, resource id or model id: every value arrives in a `PO_` variable.
- Read-only. The one exception is `f7_presigned_put.sh`, whose PUT must be refused.
- No secret value, key, token, prompt or model response in the output: counts, yes/no, exit codes,
  error codes and SHA-256 only. Names that the evidence secret scan refuses are assembled at run time.
- The last line is `RESULT=expected` or `RESULT=unexpected`; the script exits 0 when it could run, so
  that the SSM status says whether the check ran and `RESULT` says what it saw.

The collector records each script's SHA-256 (LF line endings) in `summary.json`.
