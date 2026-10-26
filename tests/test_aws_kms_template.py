"""R6 — the filled KMS template (``deploy/aws/templates/30-kms.yaml``).

Acceptance, from ``plans/aws_redeployment_tickets.md`` R6, the R6 handoff
(``plans/aws_redeployment_r6_handoff_2026-10-25.md`` §3, §4) and the
operator's answers of 2026-10-26 (decision record
``aws-redeployment-r6-kms_2026-10-26``, R6-D1 to R6-D9):

- exactly one customer-managed key and its alias ``alias/${ProjectName}``;
- the key is symmetric (``SYMMETRIC_DEFAULT``, ``ENCRYPT_DECRYPT``),
  single-Region, enabled, with rotation on every 365 days (DC-18, R6-D6);
- the key is retained on stack deletion and replacement, with a 30-day
  pending window (R6-D5);
- the key policy grants exactly: the account root (``kms:*``, the IAM
  delegation; no separate admin statement, R6-D4), the runtime role imported
  from the IAM stack (``kms:Decrypt``, ``kms:DescribeKey`` only through
  Secrets Manager and S3 in this Region, R5-D6, R6-D3), CloudTrail for the
  project trail (R6-D2) and CloudWatch Logs for the project's log groups
  (R5-D4) (DC-19);
- ``kms:Decrypt`` reaches no principal outside root, the runtime role and
  CloudWatch Logs; ``kms:*`` none but root; no ``Principal: "*"``;
- the kms stack takes no ``AdminRoleArn`` (R6-D4) and exactly the contract
  outputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools import aws_template_guard as guard

TEMPLATE = Path("deploy") / "aws" / "templates" / "30-kms.yaml"
PARAMETERS = Path("deploy") / "aws" / "parameters" / "kms.json"
CONTRACT = Path("deploy") / "aws" / "outputs_contract.json"

TRAIL_ARN = {
    "Fn::Sub": "arn:${AWS::Partition}:cloudtrail:${AWS::Region}:${AWS::AccountId}:trail/${ProjectName}-bedrock-trail"
}
TRAIL_CONTEXT = {"Fn::Sub": "arn:${AWS::Partition}:cloudtrail:*:${AWS::AccountId}:trail/*"}
LOGS_CONTEXT = {
    "Fn::Sub": "arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/${ProjectName}/*"
}
ROOT = {"Fn::Sub": "arn:${AWS::Partition}:iam::${AWS::AccountId}:root"}
RUNTIME_ROLE = {"Fn::ImportValue": "proposal-orchestrator-iam-RuntimeRoleArn"}

EXPECTED_STATEMENTS: dict[str, dict[str, Any]] = {
    "EnableRootAccountIamDelegation": {
        "Effect": "Allow",
        "Principal": {"AWS": ROOT},
        "Action": "kms:*",
        "Resource": "*",
    },
    "AllowRuntimeRoleDecryptViaServices": {
        "Effect": "Allow",
        "Principal": {"AWS": RUNTIME_ROLE},
        "Action": ["kms:Decrypt", "kms:DescribeKey"],
        "Resource": "*",
        "Condition": {
            "StringEquals": {
                "kms:ViaService": [
                    {"Fn::Sub": "secretsmanager.${AWS::Region}.amazonaws.com"},
                    {"Fn::Sub": "s3.${AWS::Region}.amazonaws.com"},
                ]
            }
        },
    },
    "AllowCloudTrailEncryptLogs": {
        "Effect": "Allow",
        "Principal": {"Service": "cloudtrail.amazonaws.com"},
        "Action": "kms:GenerateDataKey*",
        "Resource": "*",
        "Condition": {
            "StringEquals": {"aws:SourceArn": TRAIL_ARN},
            "StringLike": {"kms:EncryptionContext:aws:cloudtrail:arn": TRAIL_CONTEXT},
        },
    },
    "AllowCloudTrailDescribeKey": {
        "Effect": "Allow",
        "Principal": {"Service": "cloudtrail.amazonaws.com"},
        "Action": "kms:DescribeKey",
        "Resource": "*",
        "Condition": {"StringEquals": {"aws:SourceArn": TRAIL_ARN}},
    },
    "AllowCloudWatchLogsProjectLogGroups": {
        "Effect": "Allow",
        "Principal": {"Service": {"Fn::Sub": "logs.${AWS::Region}.amazonaws.com"}},
        "Action": [
            "kms:Encrypt",
            "kms:Decrypt",
            "kms:ReEncrypt*",
            "kms:GenerateDataKey*",
            "kms:Describe*",
        ],
        "Resource": "*",
        "Condition": {"ArnLike": {"kms:EncryptionContext:aws:logs:arn": LOGS_CONTEXT}},
    },
}


def _template() -> dict[str, Any]:
    return guard.load_template(TEMPLATE)


def _key() -> dict[str, Any]:
    return _template()["Resources"]["ProjectKey"]


def _statements() -> list[dict[str, Any]]:
    return _key()["Properties"]["KeyPolicy"]["Statement"]


def _actions(statement: dict[str, Any]) -> list[str]:
    action = statement["Action"]
    return [action] if isinstance(action, str) else list(action)


def test_exactly_the_key_and_its_alias() -> None:
    resources = _template()["Resources"]

    assert {name: r["Type"] for name, r in resources.items()} == {
        "ProjectKey": "AWS::KMS::Key",
        "ProjectKeyAlias": "AWS::KMS::Alias",
    }


def test_key_is_symmetric_single_region_enabled_with_yearly_rotation() -> None:
    props = _key()["Properties"]

    assert props["KeySpec"] == "SYMMETRIC_DEFAULT"
    assert props["KeyUsage"] == "ENCRYPT_DECRYPT"
    assert props["MultiRegion"] is False
    assert props["Enabled"] is True
    assert props["EnableKeyRotation"] is True
    assert props["RotationPeriodInDays"] == 365
    assert "Origin" not in props, "AWS_KMS key material (the default) only"
    assert "BypassPolicyLockoutSafetyCheck" not in props


def test_key_is_retained_with_a_thirty_day_window() -> None:
    key = _key()

    assert key["DeletionPolicy"] == "Retain"
    assert key["UpdateReplacePolicy"] == "Retain"
    assert key["Properties"]["PendingWindowInDays"] == 30


def test_key_carries_name_and_project_tags() -> None:
    tags = {t["Key"]: t["Value"] for t in _key()["Properties"]["Tags"]}

    assert tags == {"Name": {"Ref": "ProjectName"}, "project": {"Ref": "ProjectName"}}


def test_key_policy_is_exactly_the_decided_statements() -> None:
    policy = _key()["Properties"]["KeyPolicy"]
    statements = _statements()
    by_sid = {s["Sid"]: {k: v for k, v in s.items() if k != "Sid"} for s in statements}

    assert policy["Version"] == "2012-10-17"
    assert len(by_sid) == len(statements), "duplicate Sid"
    assert by_sid == EXPECTED_STATEMENTS


def test_principals_are_root_runtime_role_cloudtrail_and_logs_only() -> None:
    principals = [s["Principal"] for s in _statements()]

    assert all(p != "*" and p.get("AWS") != "*" for p in principals)
    aws = [p["AWS"] for p in principals if "AWS" in p]
    services = [p["Service"] for p in principals if "Service" in p]
    assert aws == [ROOT, RUNTIME_ROLE]
    assert services == [
        "cloudtrail.amazonaws.com",
        "cloudtrail.amazonaws.com",
        {"Fn::Sub": "logs.${AWS::Region}.amazonaws.com"},
    ]


def test_runtime_role_only_through_the_iam_export() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "runtime-role" not in text.replace("RuntimeRole", ""), "no literal role ARN"
    assert text.count("proposal-orchestrator-iam-RuntimeRoleArn") == 1


def test_decrypt_and_wildcards_reach_only_the_decided_principals() -> None:
    decrypt_sids = set()
    for statement in _statements():
        actions = _actions(statement)
        assert statement["Effect"] == "Allow"
        if "kms:*" in actions:
            assert statement["Sid"] == "EnableRootAccountIamDelegation"
        if "kms:Decrypt" in actions or any(a.startswith("kms:Decrypt") and a != "kms:Decrypt" for a in actions):
            decrypt_sids.add(statement["Sid"])
        assert not any(a in {"kms:Decrypt*", "kms:Encrypt*", "*"} for a in actions)

    assert decrypt_sids == {"AllowRuntimeRoleDecryptViaServices", "AllowCloudWatchLogsProjectLogGroups"}


def test_alias_is_the_project_alias_on_the_key() -> None:
    alias = _template()["Resources"]["ProjectKeyAlias"]["Properties"]

    assert alias == {"AliasName": {"Fn::Sub": "alias/${ProjectName}"}, "TargetKeyId": {"Ref": "ProjectKey"}}


def test_no_admin_role_parameter_in_the_kms_stack() -> None:
    parameters = json.loads(PARAMETERS.read_text(encoding="utf-8-sig"))

    assert "AdminRoleArn" not in _template()["Parameters"]
    assert "AdminRoleArn" not in {p["ParameterKey"] for p in parameters}


def test_outputs_are_the_contract_with_their_values() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
    (kms,) = [s for s in contract["stacks"] if s["key"] == "kms"]
    outputs = _template()["Outputs"]

    assert {k: v["Export"]["Name"] for k, v in outputs.items()} == {
        k: v["export"] for k, v in kms["outputs"].items()
    }
    assert outputs["KeyArn"]["Value"] == {"Fn::GetAtt": ["ProjectKey", "Arn"]}
    assert outputs["KeyId"]["Value"] == {"Ref": "ProjectKey"}
    assert outputs["KeyAliasName"]["Value"] == {"Ref": "ProjectKeyAlias"}


def test_metadata_names_the_fill_decision() -> None:
    meta = _template()["Metadata"]["ProposalOrchestrator"]

    assert meta["Decision"] == "aws-redeployment-od6-stack-layout-r3_2026-10-22"
    assert meta["FillDecision"] == "aws-redeployment-r6-kms_2026-10-26"
    assert Path(
        "docs/tier4_orchestration_state/decision_log/aws-redeployment-r6-kms_2026-10-26.json"
    ).exists()
