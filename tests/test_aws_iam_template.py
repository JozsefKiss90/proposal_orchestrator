"""R5 — the filled IAM template (``deploy/aws/templates/20-iam.yaml``).

Acceptance, from ``plans/aws_redeployment_tickets.md`` R5, the R5 handoff
(``plans/aws_redeployment_r5_handoff_2026-10-24.md`` §3, §4) and the
operator's answers of 2026-10-25 (decision record
``aws-redeployment-r5-iam_2026-10-25``):

- one runtime role (OD2 a) trusted by ``ec2.amazonaws.com`` only (DC-13),
  with the permission boundary (DC-12) and exactly four managed policies:
  invoke, supporting services, deploy-bucket read and the explicit deny;
  one instance profile holding that role (DC-09);
- the invoke policy names the OD7 lists through their parameters, never a
  literal; the profiles are requested in this Region, the foundation models
  only through those profiles and in the routed Regions (DC-10, R5-D3);
- the explicit deny refuses Bedrock administration, the other services,
  everything but ``eu.`` Claude profiles and Claude foundation models
  (OD7-global), S3 outside the deploy bucket's ``bundles/`` (R5-D2) and
  invoke outside the routed Regions (DC-16, R5-D3);
- the SSM Agent's actions in the boundary and the supporting-services policy
  are exactly those of the evidenced ``AmazonSSMManagedInstanceCore`` version
  (R5-D7); no ``kms:Decrypt`` in any Allow outside the boundary (R5-D6, R6);
- no S3 write anywhere; no wildcard grant outside the SSM Agent's and caller
  identity's own lines (R5-D8 c);
- the flow-logs role trusts ``vpc-flow-logs.amazonaws.com`` only, for flow
  logs of this account, and writes to ``/${ProjectName}/vpc-flow-logs`` only
  (R5-D4);
- the fixed names of R5-D5 and exactly the contract outputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

import pytest

from tools import aws_template_guard as guard

TEMPLATE = Path("deploy") / "aws" / "templates" / "20-iam.yaml"
CONTRACT = Path("deploy") / "aws" / "outputs_contract.json"
SSM_CORE_EVIDENCE = (
    Path("docs") / "infrastructure_security" / "evidence_v2" / "R5" / "R5_03_ssm-core-policy.json"
)

EXPECTED_RESOURCES = {
    "PermissionBoundary": "AWS::IAM::ManagedPolicy",
    "BedrockInvokePolicy": "AWS::IAM::ManagedPolicy",
    "ExplicitDenyPolicy": "AWS::IAM::ManagedPolicy",
    "SupportingServicesPolicy": "AWS::IAM::ManagedPolicy",
    "DeployBucketReadPolicy": "AWS::IAM::ManagedPolicy",
    "RuntimeRole": "AWS::IAM::Role",
    "RuntimeInstanceProfile": "AWS::IAM::InstanceProfile",
    "FlowLogsWritePolicy": "AWS::IAM::ManagedPolicy",
    "FlowLogsRole": "AWS::IAM::Role",
}
EXPECTED_NAMES = {
    "PermissionBoundary": "${ProjectName}-boundary",
    "BedrockInvokePolicy": "${ProjectName}-bedrock-invoke",
    "ExplicitDenyPolicy": "${ProjectName}-explicit-deny",
    "SupportingServicesPolicy": "${ProjectName}-supporting-services",
    "DeployBucketReadPolicy": "${ProjectName}-deploy-bucket-read",
    "RuntimeRole": "${ProjectName}-runtime-role",
    "RuntimeInstanceProfile": "${ProjectName}-runtime-profile",
    "FlowLogsWritePolicy": "${ProjectName}-flow-logs-write",
    "FlowLogsRole": "${ProjectName}-flow-logs-role",
}
NAME_KEYS = {
    "AWS::IAM::ManagedPolicy": "ManagedPolicyName",
    "AWS::IAM::Role": "RoleName",
    "AWS::IAM::InstanceProfile": "InstanceProfileName",
}
INVOKE = {"bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"}
S3_READ = {"s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"}
BUCKET = {"Fn::Sub": "arn:${AWS::Partition}:s3:::${ProjectName}-deploy-${AWS::AccountId}"}
BUNDLES = {"Fn::Sub": "arn:${AWS::Partition}:s3:::${ProjectName}-deploy-${AWS::AccountId}/bundles/*"}
SECRET = {"Fn::Sub": "arn:${AWS::Partition}:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${ProjectName}/env-config-*"}
LOG_GROUP = {"Fn::Sub": "arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/${ProjectName}/vpc-flow-logs:*"}
PROFILES = {"Ref": "InferenceProfileArns"}
MODELS = {"Ref": "FoundationModelArns"}
ROUTED = {"Ref": "RoutedRegions"}
SSM_NAMESPACES = ("ssm:", "ssmmessages:", "ec2messages:")
ALLOW_POLICIES = ("BedrockInvokePolicy", "SupportingServicesPolicy", "DeployBucketReadPolicy", "FlowLogsWritePolicy")


@pytest.fixture(scope="module")
def template() -> dict[str, Any]:
    return guard.load_template(TEMPLATE)


@pytest.fixture(scope="module")
def resources(template: dict[str, Any]) -> dict[str, Any]:
    return template["Resources"]


def _props(resources: dict[str, Any], logical_id: str) -> dict[str, Any]:
    return resources[logical_id]["Properties"]


def _statements(resources: dict[str, Any], logical_id: str) -> list[dict[str, Any]]:
    document = _props(resources, logical_id)["PolicyDocument"]
    assert document["Version"] == "2012-10-17", logical_id
    return document["Statement"]


def _by_sid(resources: dict[str, Any], logical_id: str) -> dict[str, dict[str, Any]]:
    statements = _statements(resources, logical_id)
    sids = [s["Sid"] for s in statements]
    assert len(sids) == len(set(sids)), logical_id
    return dict(zip(sids, statements))


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def _actions(statement: dict[str, Any]) -> set[str]:
    return set(_list(statement["Action"]))


def _all_allow_statements(resources: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    for logical_id, resource in resources.items():
        if resource["Type"] == "AWS::IAM::ManagedPolicy":
            for statement in _statements(resources, logical_id):
                if statement["Effect"] == "Allow":
                    yield logical_id, statement


def _ssm_core_actions() -> set[str]:
    evidence = json.loads(SSM_CORE_EVIDENCE.read_text(encoding="utf-8-sig"))
    version = evidence["PolicyVersion"]
    assert version["IsDefaultVersion"] is True and version["VersionId"] == "v2"
    actions: set[str] = set()
    for statement in version["Document"]["Statement"]:
        assert statement["Effect"] == "Allow" and statement["Resource"] == "*"
        actions |= set(_list(statement["Action"]))
    return actions


def _ssm_actions_in(resources: dict[str, Any], logical_id: str) -> set[str]:
    found: set[str] = set()
    for statement in _statements(resources, logical_id):
        if all(a.startswith(SSM_NAMESPACES) for a in _actions(statement)):
            assert statement["Effect"] == "Allow" and statement["Resource"] == "*"
            found |= _actions(statement)
    return found


# --- shape, names, tags ---------------------------------------------------------


def test_exactly_the_expected_resources(resources: dict[str, Any]) -> None:
    assert {k: v["Type"] for k, v in resources.items()} == EXPECTED_RESOURCES
    assert "SkeletonPlaceholder" not in resources
    assert guard.check_template(TEMPLATE) == []


def test_fixed_names_under_the_root_path(resources: dict[str, Any]) -> None:
    """R5-D5: fixed names (CAPABILITY_NAMED_IAM), stable ARNs for R6, R8 and R11."""
    for logical_id, name in EXPECTED_NAMES.items():
        props = _props(resources, logical_id)
        assert props[NAME_KEYS[resources[logical_id]["Type"]]] == {"Fn::Sub": name}, logical_id
        assert props["Path"] == "/", logical_id


def test_roles_carry_name_and_project_tags_and_untaggable_types_none(resources: dict[str, Any]) -> None:
    for logical_id, resource in resources.items():
        props = resource["Properties"]
        if resource["Type"] in guard.UNTAGGABLE_TYPES:
            assert "Tags" not in props, logical_id
            continue
        tags = {t["Key"]: t["Value"] for t in props["Tags"]}
        assert tags == {"Name": {"Fn::Sub": EXPECTED_NAMES[logical_id]}, "project": {"Ref": "ProjectName"}}


def test_metadata_names_the_fill_decision(template: dict[str, Any]) -> None:
    meta = template["Metadata"]["ProposalOrchestrator"]
    assert meta["FilledBy"] == "R5"
    assert meta["FillDecision"] == "aws-redeployment-r5-iam_2026-10-25"
    assert Path("docs/tier4_orchestration_state/decision_log/aws-redeployment-r5-iam_2026-10-25.json").is_file()


# --- runtime role and instance profile (DC-09, DC-12, DC-13) ---------------------


def test_runtime_role_is_trusted_by_ec2_only(resources: dict[str, Any]) -> None:
    trust = _props(resources, "RuntimeRole")["AssumeRolePolicyDocument"]
    (statement,) = trust["Statement"]

    assert statement["Effect"] == "Allow"
    assert statement["Principal"] == {"Service": "ec2.amazonaws.com"}
    assert statement["Action"] == "sts:AssumeRole"
    assert "NotPrincipal" not in statement


def test_runtime_role_has_the_boundary_and_exactly_four_policies(resources: dict[str, Any]) -> None:
    role = _props(resources, "RuntimeRole")

    assert role["PermissionsBoundary"] == {"Ref": "PermissionBoundary"}
    assert sorted(p["Ref"] for p in role["ManagedPolicyArns"]) == sorted(
        ["BedrockInvokePolicy", "SupportingServicesPolicy", "DeployBucketReadPolicy", "ExplicitDenyPolicy"]
    )
    assert "Policies" not in role, "no inline policy"


def test_instance_profile_holds_the_runtime_role_only(resources: dict[str, Any]) -> None:
    assert _props(resources, "RuntimeInstanceProfile")["Roles"] == [{"Ref": "RuntimeRole"}]


# --- invoke policy (DC-10, F2, R5-D3) --------------------------------------------


def test_invoke_policy_names_the_od7_lists_with_their_conditions(resources: dict[str, Any]) -> None:
    statements = _by_sid(resources, "BedrockInvokePolicy")
    assert set(statements) == {"InvokeOd7Profiles", "InvokeRoutedModelsThroughOd7Profiles"}

    profiles = statements["InvokeOd7Profiles"]
    assert profiles["Effect"] == "Allow" and _actions(profiles) == INVOKE
    assert profiles["Resource"] == PROFILES
    assert profiles["Condition"] == {"StringEquals": {"aws:RequestedRegion": {"Ref": "AWS::Region"}}}

    models = statements["InvokeRoutedModelsThroughOd7Profiles"]
    assert models["Effect"] == "Allow" and _actions(models) == INVOKE
    assert models["Resource"] == MODELS
    assert models["Condition"] == {
        "StringEquals": {"bedrock:InferenceProfileArn": PROFILES, "aws:RequestedRegion": ROUTED}
    }, "R5-D3: a routed model is authorised with its own Region as aws:RequestedRegion"


def test_no_bedrock_arn_is_a_literal_anywhere(template: dict[str, Any]) -> None:
    text = json.dumps(template["Resources"])
    assert "arn:aws:bedrock" not in text
    assert "anthropic.claude-opus" not in text and "anthropic.claude-sonnet" not in text


# --- explicit deny (DC-11, DC-16, OD7-global, R5-D2) -----------------------------


def test_explicit_deny_statements(resources: dict[str, Any]) -> None:
    statements = _by_sid(resources, "ExplicitDenyPolicy")
    assert set(statements) == {
        "DenyBedrockAdministration",
        "DenyOtherServices",
        "DenyNonClaudeAndNonEuProfiles",
        "DenyS3OutsideDeployBundles",
        "DenyInvokeOutsideApprovedRegions",
    }
    assert all(s["Effect"] == "Deny" for s in statements.values())

    admin = statements["DenyBedrockAdministration"]
    assert {"bedrock:PutModelInvocationLoggingConfiguration", "bedrock:DeleteModelInvocationLoggingConfiguration"} <= _actions(admin)
    assert {"bedrock:CreateModelCustomizationJob", "bedrock:CreateProvisionedModelThroughput"} <= _actions(admin)
    assert admin["Resource"] == "*"

    others = statements["DenyOtherServices"]
    assert _actions(others) == {"iam:*", "ec2:*", "lambda:*", "sqs:*", "sns:*", "dynamodb:*"}
    assert others["Resource"] == "*"


def test_deny_admits_only_eu_claude_profiles_and_claude_models(resources: dict[str, Any]) -> None:
    deny = _by_sid(resources, "ExplicitDenyPolicy")["DenyNonClaudeAndNonEuProfiles"]
    assert _actions(deny) == INVOKE and "Resource" not in deny

    not_resource = [a["Fn::Sub"] for a in deny["NotResource"]]
    assert not_resource == [
        "arn:${AWS::Partition}:bedrock:*:${AWS::AccountId}:inference-profile/eu.anthropic.claude-*",
        "arn:${AWS::Partition}:bedrock:*::foundation-model/anthropic.claude-*",
    ]
    text = json.dumps(deny)
    assert "us.anthropic" not in text and "global." not in text and "application-inference-profile" not in text


def test_deny_s3_outside_the_deploy_bundles(resources: dict[str, Any]) -> None:
    deny = _by_sid(resources, "ExplicitDenyPolicy")["DenyS3OutsideDeployBundles"]
    assert deny["Action"] == "s3:*"
    assert deny["NotResource"] == [BUCKET, BUNDLES]


def test_deny_invoke_outside_the_routed_regions(resources: dict[str, Any]) -> None:
    deny = _by_sid(resources, "ExplicitDenyPolicy")["DenyInvokeOutsideApprovedRegions"]
    assert _actions(deny) == INVOKE and deny["Resource"] == "*"
    assert deny["Condition"] == {"StringNotEquals": {"aws:RequestedRegion": ROUTED}}


# --- boundary (DC-12) and supporting services (R5-D6, R5-D7) ----------------------


def test_boundary_allows_exactly_what_the_host_needs(resources: dict[str, Any]) -> None:
    statements = _by_sid(resources, "PermissionBoundary")
    assert all(s["Effect"] == "Allow" for s in statements.values())

    assert _actions(statements["BedrockInvokeProfiles"]) == INVOKE
    assert statements["BedrockInvokeProfiles"]["Resource"] == PROFILES
    assert _actions(statements["BedrockInvokeRoutedModels"]) == INVOKE
    assert statements["BedrockInvokeRoutedModels"]["Resource"] == MODELS
    assert statements["RuntimeSecretRead"] == {
        "Sid": "RuntimeSecretRead", "Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": SECRET,
    }
    assert _actions(statements["KmsDecryptThroughKeyPolicy"]) == {"kms:Decrypt", "kms:DescribeKey"}
    assert statements["KmsDecryptThroughKeyPolicy"]["Resource"] == {
        "Fn::Sub": "arn:${AWS::Partition}:kms:${AWS::Region}:${AWS::AccountId}:key/*"
    }
    assert statements["CallerIdentity"]["Action"] == "sts:GetCallerIdentity"
    assert _actions(statements["DeployBucketBundlesRead"]) == {"s3:ListBucket", "s3:GetBucketLocation"}
    assert statements["DeployBucketBundlesRead"]["Resource"] == BUCKET
    assert statements["DeployBucketBundlesObjects"]["Action"] == "s3:GetObject"
    assert statements["DeployBucketBundlesObjects"]["Resource"] == BUNDLES

    every_action = set().union(*(_actions(s) for s in statements.values()))
    assert every_action == (
        INVOKE
        | {"secretsmanager:GetSecretValue", "kms:Decrypt", "kms:DescribeKey", "sts:GetCallerIdentity"}
        | S3_READ
        | _ssm_core_actions()
    ), "nothing else (DC-12)"
    assert not any(a.startswith("kms:GenerateDataKey") for a in every_action), "R5-D6"


def test_ssm_actions_are_the_evidenced_managed_policy_version(resources: dict[str, Any]) -> None:
    core = _ssm_core_actions()
    assert len(core) == 25
    assert _ssm_actions_in(resources, "PermissionBoundary") == core
    assert _ssm_actions_in(resources, "SupportingServicesPolicy") == core


def test_supporting_services_policy(resources: dict[str, Any]) -> None:
    statements = _by_sid(resources, "SupportingServicesPolicy")
    every_action = set().union(*(_actions(s) for s in statements.values()))

    assert every_action == _ssm_core_actions() | {"sts:GetCallerIdentity", "secretsmanager:GetSecretValue"}
    assert statements["RuntimeSecretRead"]["Resource"] == SECRET


def test_kms_decrypt_is_granted_by_no_identity_policy(resources: dict[str, Any]) -> None:
    """R6 grants Decrypt through the key policy; the boundary only admits it."""
    for logical_id, statement in _all_allow_statements(resources):
        if logical_id != "PermissionBoundary":
            assert not any(a.startswith("kms:") for a in _actions(statement)), logical_id


# --- S3 (F7, R5-D1) and wildcard grants (R5-D8 c) -------------------------------


def test_deploy_bucket_read_is_bundles_prefix_only(resources: dict[str, Any]) -> None:
    statements = _by_sid(resources, "DeployBucketReadPolicy")
    assert statements["ListBundlesPrefix"]["Action"] == "s3:ListBucket"
    assert statements["ListBundlesPrefix"]["Resource"] == BUCKET
    assert statements["ListBundlesPrefix"]["Condition"] == {"StringLike": {"s3:prefix": "bundles/*"}}
    assert statements["BucketLocation"]["Action"] == "s3:GetBucketLocation"
    assert statements["BucketLocation"]["Resource"] == BUCKET
    assert statements["GetBundles"]["Action"] == "s3:GetObject"
    assert statements["GetBundles"]["Resource"] == BUNDLES


def test_no_s3_write_is_granted_anywhere(resources: dict[str, Any]) -> None:
    for logical_id, statement in _all_allow_statements(resources):
        s3 = {a for a in _actions(statement) if a.startswith("s3:")}
        assert s3 <= S3_READ, (logical_id, s3)
        for resource in _list(statement["Resource"]):
            if isinstance(resource, dict) and ":s3:::" in resource.get("Fn::Sub", ""):
                assert resource in (BUCKET, BUNDLES), (logical_id, resource)


def test_no_wildcard_grant(resources: dict[str, Any]) -> None:
    """No Allow of Action '*' or 'service:*'; Resource '*' only for the SSM Agent and caller identity."""
    for logical_id, statement in _all_allow_statements(resources):
        actions = _actions(statement)
        assert "NotAction" not in statement and "NotResource" not in statement, logical_id
        assert not any(a == "*" or a.endswith(":*") for a in actions), (logical_id, actions)
        if statement["Resource"] == "*" or "*" in _list(statement["Resource"]):
            assert all(a.startswith(SSM_NAMESPACES) or a == "sts:GetCallerIdentity" for a in actions), (
                logical_id,
                actions,
            )


def test_allow_policies_are_attached_where_expected(resources: dict[str, Any]) -> None:
    attached = {p["Ref"] for p in _props(resources, "RuntimeRole")["ManagedPolicyArns"]}
    attached |= {p["Ref"] for p in _props(resources, "FlowLogsRole")["ManagedPolicyArns"]}
    assert set(ALLOW_POLICIES) <= attached
    for logical_id in ALLOW_POLICIES + ("PermissionBoundary", "ExplicitDenyPolicy"):
        props = _props(resources, logical_id)
        for key in ("Roles", "Users", "Groups"):
            assert key not in props, f"{logical_id} attaches through the role, not through {key}"


# --- flow-logs role (R5-D4) -------------------------------------------------------


def test_flow_logs_role_is_trusted_by_flow_logs_of_this_account_only(resources: dict[str, Any]) -> None:
    role = _props(resources, "FlowLogsRole")
    (statement,) = role["AssumeRolePolicyDocument"]["Statement"]

    assert statement["Effect"] == "Allow"
    assert statement["Principal"] == {"Service": "vpc-flow-logs.amazonaws.com"}
    assert statement["Action"] == "sts:AssumeRole"
    assert statement["Condition"] == {
        "StringEquals": {"aws:SourceAccount": {"Ref": "AWS::AccountId"}},
        "ArnLike": {"aws:SourceArn": {"Fn::Sub": "arn:${AWS::Partition}:ec2:${AWS::Region}:${AWS::AccountId}:vpc-flow-log/*"}},
    }
    assert [p["Ref"] for p in role["ManagedPolicyArns"]] == ["FlowLogsWritePolicy"]


def test_flow_logs_policy_writes_to_the_one_log_group(resources: dict[str, Any]) -> None:
    (statement,) = _statements(resources, "FlowLogsWritePolicy")
    assert statement["Effect"] == "Allow"
    assert _actions(statement) == {
        "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogGroups", "logs:DescribeLogStreams",
    }
    assert statement["Resource"] == LOG_GROUP


# --- outputs ----------------------------------------------------------------------


def test_outputs_point_at_the_right_resources(template: dict[str, Any]) -> None:
    outputs = {k: v["Value"] for k, v in template["Outputs"].items()}

    assert outputs == {
        "RuntimeRoleName": {"Ref": "RuntimeRole"},
        "RuntimeRoleArn": {"Fn::GetAtt": ["RuntimeRole", "Arn"]},
        "InstanceProfileName": {"Ref": "RuntimeInstanceProfile"},
        "InstanceProfileArn": {"Fn::GetAtt": ["RuntimeInstanceProfile", "Arn"]},
        "PermissionBoundaryArn": {"Ref": "PermissionBoundary"},
        "ExplicitDenyPolicyArn": {"Ref": "ExplicitDenyPolicy"},
        "FlowLogsRoleArn": {"Fn::GetAtt": ["FlowLogsRole", "Arn"]},
    }
    contract = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
    (iam,) = [s for s in contract["stacks"] if s["key"] == "iam"]
    assert set(outputs) == set(iam["outputs"])
