# Audit package amendment draft — the anonymisation bundle (AN12)

| Field | Value |
|---|---|
| Status | **Draft, awaiting operator approval.** Nothing below is applied to the audit package yet. |
| Date | 2026-10-16 |
| Decision | AN12 D2 (operator, 2026-10-16): draft now, approve before host step 6 installs the interpreter. |
| Decision record | `docs/tier4_orchestration_state/decision_log/msca-dn-an12-offline-bundle_2026-10-16.json` |
| Scope | ADR-001 Decision 8, RSK-12, the deployment guide and the operational procedure. |

## Why an amendment is needed

AN12 adds a second deployment bundle to the host. It carries its own Python interpreter, which the approved audit package does not mention.

The approved text describes one bundle: Python 3.9.25 from the host, pip bootstrapped by `ensurepip`, and four direct dependencies (ADR-001 Decision 8, RSK-12, deployment guide §4). That bundle and its install at `/opt/proposal-orchestrator` are unchanged.

The amendments add text and replace no approved wording, so the June 2026 position stays readable.

## The facts the amendments rest on

Each fact is measured from a committed file or a run on 2026-10-16.

| Fact | Source |
|---|---|
| PyMuPDF 1.28.2, the extraction pin, publishes no wheel for Python 3.9. The newest 3.9 wheel is 1.26.5. | `pip download`, decision record D1 |
| The bundle ships CPython 3.11.16 from python-build-standalone release 20260929. | `deploy/offline_bundle.json` |
| The interpreter archive's sha256 is `fbbfd0f2253996486455f44a28c09ac7e2df534b8a4835408d17c99d185b80ec`, matched against the release's `SHA256SUMS`. | `deploy/offline_bundle.json` |
| Sixteen distributions are pinned, each by version and one sha256. | `deploy/requirements-host.txt` |
| The host installs with `pip install --no-index --require-hashes` from the bundled wheels only. | `deploy/install_host.sh` |
| The install goes into a new directory, `/opt/msca-dn-anonymisation`, and refuses one that exists. The host's system Python is not touched. | `deploy/install_host.sh` |
| The bundle holds committed files only, bound by sha256 in `bundle_manifest.json`. Two builds of one commit are byte-equal. | `runner/offline_bundle.py`, `tests/runner/test_offline_bundle.py` |
| On the host, `verify` checks the files, interpreter, glibc, pins and ADR-001 settings. It also checks that Bedrock resolves to private addresses and that an internet endpoint is unreachable. | `runner/offline_bundle.py` |

The sixteen distributions are boto3, botocore, jmespath, python-dateutil, s3transfer, six, urllib3, pyyaml, jsonschema, attrs, jsonschema-specifications, referencing, rpds-py, typing-extensions, python-dotenv and pymupdf.

## A1 — ADR-001 header

Add one row to the header table, after `Date`:

> | Amended | 2026-10-16, amendment A1 to Decision 8 (the anonymisation bundle, MSCA-DN ticket AN12) |

## A2 — ADR-001 Decision 8, a new closing subsection

Append after Decision 8's `### Evidence` list:

> ### Amendment A1 (2026-10-16) — The anonymisation bundle

> A second offline bundle carries the MSCA-DN anonymisation pipeline to the same host. It follows this decision's route: built on the operator's workstation, uploaded to S3 and installed through the S3 gateway endpoint. The host never contacts PyPI.

> The bundle carries its own interpreter, CPython 3.11.16 from python-build-standalone release 20260929. The pipeline's extraction library, PyMuPDF 1.28.2, publishes no wheel for the host's Python 3.9. The interpreter archive is pinned by sha256 and checked against the release's published checksums before bundling.

> The dependency set is sixteen distributions, pinned by version and hash in `deploy/requirements-host.txt`. The host installs them with `--no-index --require-hashes`, so a changed or substituted wheel stops the install. The bundle is built from committed files only, and two builds of one commit are byte-equal.

> The bundle installs into its own directory and leaves the host's Python 3.9 and the orchestrator install unchanged. After install, `python -m runner.offline_bundle verify` records the installed files, the interpreter, the ADR-001 environment controls, the Bedrock endpoint's private resolution and an unreachable internet endpoint.

> **Trade-off.** The interpreter is a binary from a third-party build project, outside the AL2023 package set. RSK-12 covers it.

> **Evidence.** `deploy/offline_bundle.json`, `deploy/requirements-host.txt`, the host verification record, and the decision record `msca-dn-an12-offline-bundle_2026-10-16`.

## A3 — RSK-12 in the risk acceptance register

Replace three rows of the RSK-12 table. The other rows are unchanged.

| Row | Proposed text |
|---|---|
| Risk description | A Python dependency or a bundled interpreter contains a vulnerability or is compromised at its source, introducing a security weakness into the application runtime. The orchestrator bundle depends on boto3, pyyaml, jsonschema and python-dotenv. The anonymisation bundle depends on sixteen pinned distributions, including PyMuPDF, and on a CPython 3.11.16 interpreter from python-build-standalone. |
| Mitigation | Both bundles use pre-downloaded wheels and install without PyPI; the host has no internet route. The anonymisation bundle pins every distribution and the interpreter archive by sha256, the build refuses any mismatch, and the host installs with `--require-hashes`. The interpreter's hash is checked against the release's published checksums. |
| Evidence | Deployment guide §4 (offline wheel installation); `deploy/requirements-host.txt` and `deploy/offline_bundle.json`; the AN12 host verification record; DC-32 (no internet egress). |

**For the operator:** likelihood Low, impact Medium and residual risk Low are proposed unchanged. Hash pinning narrows substitution, but the interpreter widens what the host trusts, so this rating is your judgement.

## A4 — Deployment guide

Add one row to the Deployment Status table:

> | Anonymisation bundle (AN12) | PENDING | — | `/opt/msca-dn-anonymisation`, bundled CPython 3.11.16, procedure `plans/msca_dn_an12_host_runbook.md` |

Add a short section after §11:

> ## 12. The anonymisation bundle (AN12)

> A second bundle carries the MSCA-DN anonymisation pipeline with its own Python 3.11 interpreter (ADR-001 Decision 8, amendment A1). Sections 4 and 5 still govern the orchestrator bundle.

> The procedure is `plans/msca_dn_an12_host_runbook.md`. It builds the bundle with `python -m runner.offline_bundle build`, installs it with `deploy/install_host.sh` and records `python -m runner.offline_bundle verify`.

> Use region `us-east-1`. The VPC's only Bedrock endpoint is `com.amazonaws.us-east-1.bedrock-runtime` (DC-01).

## A5 — Operational procedure §7.2

Append to §7.2, "Updating the Deployment Bundle":

> 4. The anonymisation bundle is not rebuilt with `pip download --python-version 3.9`. Change `deploy/requirements-host.txt` or `deploy/offline_bundle.json`, commit, and rebuild with `python -m runner.offline_bundle build` (deployment guide §12).

## Left for the operator

- **The zip.** `audit_package/audit_package.zip` is the 2026-06-03 snapshot. Whether to reissue it after approval is your call.
- **The control register.** No DC changes. The `verify` record's `private_endpoint` check is new evidence for DC-02 and could be cited there.
