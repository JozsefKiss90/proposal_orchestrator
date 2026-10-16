# AN12 runbook: offline bundle and private-host smoke run

This runbook covers ticket AN12 of `.scratch/msca-dn-anonymisation/tickets.md`. The operator performs every step below. The code is in `runner/offline_bundle.py`, `tools/anonymisation_host_smoke.py` and `harness/commands/converse_smoke.py`. The decision record is `docs/tier4_orchestration_state/decision_log/msca-dn-an12-offline-bundle_2026-10-16.json`.

`tests/test_anonymisation_host_runbook.py` parses every `python -m` line here against its command's parser.

## What changed from the deployment guide

The guide's bundle installs into the host's system Python 3.9.25. That route cannot carry this pipeline. PyMuPDF 1.28.2 is the extraction pin, and it publishes no wheel for Python 3.9.

This bundle carries its own interpreter instead: CPython 3.11.16 from python-build-standalone, pinned by hash in `deploy/offline_bundle.json`. Python 3.11 is one of the two interpreters the pin was measured on. The system Python is left untouched.

Every wheel is pinned by hash in `deploy/requirements-host.txt`. The host installs with `--no-index --require-hashes`, so a missing, extra or altered wheel stops the install.

## Part 1: on the workstation (internet access)

Work from a clean checkout of the commit you intend to deploy. The bundle carries HEAD as committed, so uncommitted edits never reach the host. Keep the downloads and the output outside the repository.

1. Download the wheels for the host's interpreter and platform:

   ```bash
   py -3.10 -m pip download --require-hashes -r deploy/requirements-host.txt -d <wheels-dir> \
     --only-binary=:all: --implementation cp --python-version 3.11 \
     --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux_2_28_x86_64
   ```

2. Download the interpreter archive named in `deploy/offline_bundle.json` (`interpreter.url`) into `<downloads-dir>`. The build checks its hash against the spec.

3. Build the bundle:

   ```bash
   py -3.10 -m runner.offline_bundle build --wheels <wheels-dir> \
     --interpreter <downloads-dir>/cpython-3.11.16+20260929-x86_64-unknown-linux-gnu-install_only.tar.gz \
     --out-dir <out-dir>
   ```

   The build refuses a wheel set that does not match the pins both ways, and a wheel that needs a newer glibc than 2.34. It also refuses an interpreter that does not match the pinned hash. It prints the tarball's sha256 and writes it beside the tarball as `msca-dn-anonymisation-host.tar.gz.sha256`.

4. Upload the tarball and its `.sha256` file to the deployment bucket, as in deployment guide §4.3.

## Part 2: on the host (no internet route)

Work in an SSM session as `ssm-user`. Keep every output under a private working directory outside the install, here `/home/ssm-user/an12`.

5. Download the two files through the S3 gateway endpoint. Then check the tarball: `sha256sum -c msca-dn-anonymisation-host.tar.gz.sha256`.

6. Extract into `/tmp` and install into a new directory:

   ```bash
   tar xzf msca-dn-anonymisation-host.tar.gz -C /tmp
   bash /tmp/msca-dn-anonymisation-host/app/deploy/install_host.sh /opt/msca-dn-anonymisation
   ```

   The script checks `SHA256SUMS`, extracts the interpreter, installs the wheels offline and verifies every installed file against `bundle_manifest.json`. It ends with `INSTALL_COMPLETE`.

7. Load the production environment, then verify the install. This record is the evidence for criterion 1.

   ```bash
   export ORCHESTRATOR_PRODUCTION_MODE=true
   export ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata
   export ORCHESTRATOR_TRANSPORT_BACKEND=bedrock_converse
   export AWS_REGION=us-east-1
   cd /opt/msca-dn-anonymisation/app
   ../python/bin/python3 -m runner.offline_bundle verify --probe-no-internet pypi.org:443 \
     --record /home/ssm-user/an12/verification.json
   ```

   Exit status 0 means every check passed. The probe passes only when `pypi.org:443` is unreachable. Without `--probe-no-internet` the route is not measured, and the record does not pass.

   The `private_endpoint` check resolves `bedrock-runtime.<region>.amazonaws.com` and passes only when every address is private. That is the VPC endpoint of ADR-001 DC-02.

   If the probe's detail says the name did not resolve, the route was not measured. Rerun the command with an IP address, such as `--probe-no-internet 1.1.1.1:443`.

## Part 3: the pipeline on the synthetic fixture (criterion 2)

The A3 and A5 models are the operator's O2 choice, and A5 must be a different Claude model from A3. Use `us.anthropic.claude-*` inference profiles or bare `anthropic.claude-*` ids in `us-east-1`. The host's only Bedrock endpoint is in `us-east-1` (DC-01), and the invoke policy allows only those two id forms (DC-10). The token budgets are also the operator's choice. Each model stage stops when its budget is reached, and the status file records the tokens each stage used.

8. Run the automatic stages:

   ```bash
   ../python/bin/python3 -m tools.anonymisation_host_smoke --root /home/ssm-user/an12/pipeline \
     --region us-east-1 --a3-model <A3-model-id> --a5-model <A5-model-id> \
     --max-output-tokens 2000 --a3-token-budget 100000 --a5-token-budget 200000
   ```

   Exit status 3 means the run is waiting for you. It writes `operator/figure_review_template.json`, which lists the pages whose figures you must look at.

9. Look at those pages of `a4/synthesised.pdf`. The fixture is synthetic and holds no private content.

   Copy the template, replace every `<placeholder>`, and rerun step 8 with `--figure-review <your-copy>`. The model stages replay their checkpoints, so the rerun makes no model call.

10. The run then writes `operator/acceptance_input_template.json`, with the derivative's hash and the bundle's revision filled in. Copy it, attest, sign and fill the export rule, then rerun step 8 with both flags:

    ```bash
    ../python/bin/python3 -m tools.anonymisation_host_smoke --root /home/ssm-user/an12/pipeline \
      --region us-east-1 --a3-model <A3-model-id> --a5-model <A5-model-id> \
      --max-output-tokens 2000 --a3-token-budget 100000 --a5-token-budget 200000 \
      --figure-review <review-copy> --acceptance-input <acceptance-copy>
    ```

    Exit status 0 and outcome `accepted` close criterion 2. If the live A3 model proposed an edit, A7 refuses the plan, because no stage applies an A3 plan yet (AN6, AN11). That refusal is correct. Record it as the run's result rather than editing anything.

The policy the run uses is a synthetic successor that sets the research-group threshold for the fixture only. `smoke_status.json` says so. It is never used for AN13.

## Part 4: the Converse blind pass (criterion 3)

The assessor model must not be the drafter's model in any id form (AN1c). Its version tag must name `bedrock-converse`.

11. Prepare the pass. This step makes no model call:

    ```bash
    ../python/bin/python3 -m harness.commands.converse_smoke prepare --root /home/ssm-user/an12/converse \
      --assessor-model <assessor-model-id> --assessor-version bedrock-converse-us-east-1@<YYYY-MM-DD>
    ```

    It builds the synthetic world, runs the preflight and writes `receipt_draft.json`. The draft holds the request the assessor will send, built by the transport's own builder. Everything you attest is left as a `<placeholder>`.

12. Copy the draft outside the install and fill every placeholder. Then run the pass:

    ```bash
    ../python/bin/python3 -m harness.commands.converse_smoke assess --root /home/ssm-user/an12/converse       --receipt /home/ssm-user/an12/readiness_receipt.json
    ```

    The command refuses before any model call unless the receipt is green, as V13 requires before a private run. It then assesses, writes the checkpoint the receipt names, freezes, and reads the receipt against the blind report. Exit status 0 (`receipt green`) closes criterion 3. Exit status 1 lists each finding, and exit status 2 is a refusal.

13. To read the receipt again later, run the same command with `check` in place of `assess`:

    ```bash
    ../python/bin/python3 -m harness.commands.converse_smoke check --root /home/ssm-user/an12/converse       --receipt /home/ssm-user/an12/readiness_receipt.json
    ```

The blind pass has no token budget of its own. Its size is fixed by the synthetic world: three criteria at the command's default sample counts.

## What comes back

Only metadata leaves the host: `verification.json`, `pipeline/smoke_status.json`, the freeze record under `converse/baseline/`, and the `assess` output. None of these quotes document text, and the fixture is synthetic. Record the outcome in Tier 4 as a successor to the AN12 decision record. Then tick the ticket's criteria.
