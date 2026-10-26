"""R7 — the filled audit and storage template (``deploy/aws/templates/40-audit.yaml``).

Acceptance, from ``plans/aws_redeployment_tickets.md`` R7, the R7 handoff
(``plans/aws_redeployment_r7_handoff_2026-10-26.md`` §1, §3, §4) and the
operator's answers of 2026-10-26 (decision record
``aws-redeployment-r7-audit_2026-10-26``, R7-D1 to R7-D16):

- exactly two buckets with their policies, the trail, the flow-log group and
  one flow log;
- both buckets: derived names, SSE-KMS with the imported CMK (no S3 Bucket Key
  on the trail bucket, R6-D10; a Bucket Key on the deploy bucket), Block
  Public Access, versioning, ``BucketOwnerEnforced``, retained (DC-25);
- the trail bucket's lifecycle (DC-27) and the deploy bucket's;
- the trail bucket policy is the v1 policy with new ARNs; the deploy bucket
  policy is deny-only: insecure transport, principals outside the account,
  encryption headers other than the CMK, and the runtime role outside
  ``bundles/`` read (R5-D1);
- the trail is the R6-D2 trail with the CMK and log-file integrity digests,
  management events by default (DC-23, DC-24);
- the flow-log group is the R5-D4 group with the CMK and 90-day retention
  (DC-30); one flow log on the VPC, traffic ALL (DC-08);
- the stack imports exactly the exports whose contract consumers name R7,
  and has exactly the contract outputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools import aws_template_guard as guard

TEMPLATE = Path("deploy") / "aws" / "templates" / "40-audit.yaml"
KMS_TEMPLATE = Path("deploy") / "aws" / "templates" / "30-kms.yaml"
IAM_TEMPLATE = Path("deploy") / "aws" / "templates" / "20-iam.yaml"
CONTRACT = Path("deploy") / "aws" / "outputs_contract.json"
RECORD = Path("docs/tier4_orchestration_state/decision_log/aws-redeployment-r7-audit_2026-10-26.json")

KEY = {"Fn::ImportValue": "proposal-orchestrator-kms-KeyArn"}
RUNTIME_ROLE = {"Fn::ImportValue": "proposal-orchestrator-iam-RuntimeRoleArn"}
TRAIL_ARN = {
    "Fn::Sub": "arn:${AWS::Partition}:cloudtrail:${AWS::Region}:${AWS::AccountId}:trail/${ProjectName}-bedrock-trail"
}
TRAIL_BUCKET_ARN = {"Fn::GetAtt": ["TrailBucket", "Arn"]}
TRAIL_OBJECTS = {"Fn::Sub": "${TrailBucket.Arn}/*"}
DEPLOY_BUCKET_ARN = {"Fn::GetAtt": ["DeployBucket", "Arn"]}
DEPLOY_OBJECTS = {"Fn::Sub": "${DeployBucket.Arn}/*"}
PUBLIC_ACCESS_BLOCK = {
    "BlockPublicAcls": True,
    "IgnorePublicAcls": True,
    "BlockPublicPolicy": True,
    "RestrictPublicBuckets": True,
}
INSECURE_TRANSPORT = {"Bool": {"aws:SecureTransport": "false"}}
RUNTIME_ONLY = {"ArnEquals": {"aws:PrincipalArn": RUNTIME_ROLE}}

EXPECTED_TRAIL_BUCKET_POLICY: dict[str, dict[str, Any]] = {
    "AWSCloudTrailAclCheck": {
        "Effect": "Allow",
        "Principal": {"Service": "cloudtrail.amazonaws.com"},
        "Action": "s3:GetBucketAcl",
        "Resource": TRAIL_BUCKET_ARN,
        "Condition": {"StringEquals": {"aws:SourceArn": TRAIL_ARN}},
    },
    "AWSCloudTrailWrite": {
        "Effect": "Allow",
        "Principal": {"Service": "cloudtrail.amazonaws.com"},
        "Action": "s3:PutObject",
        "Resource": {"Fn::Sub": "${TrailBucket.Arn}/cloudtrail/${ProjectName}/AWSLogs/${AWS::AccountId}/*"},
        "Condition": {
            "StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control", "aws:SourceArn": TRAIL_ARN}
        },
    },
    "DenyUnencryptedObjects": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:PutObject",
        "Resource": TRAIL_OBJECTS,
        "Condition": {"StringNotEquals": {"s3:x-amz-server-side-encryption": "aws:kms"}},
    },
    "DenyInsecureTransport": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [TRAIL_BUCKET_ARN, TRAIL_OBJECTS],
        "Condition": INSECURE_TRANSPORT,
    },
}

EXPECTED_DEPLOY_BUCKET_POLICY: dict[str, dict[str, Any]] = {
    "DenyInsecureTransport": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [DEPLOY_BUCKET_ARN, DEPLOY_OBJECTS],
        "Condition": INSECURE_TRANSPORT,
    },
    "DenyPrincipalsOutsideAccount": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [DEPLOY_BUCKET_ARN, DEPLOY_OBJECTS],
        "Condition": {"StringNotEquals": {"aws:PrincipalAccount": {"Ref": "AWS::AccountId"}}},
    },
    "DenyEncryptionHeaderOtherThanKms": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:PutObject",
        "Resource": DEPLOY_OBJECTS,
        "Condition": {
            "Null": {"s3:x-amz-server-side-encryption": "false"},
            "StringNotEquals": {"s3:x-amz-server-side-encryption": "aws:kms"},
        },
    },
    "DenyKmsHeaderWithoutKeyId": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:PutObject",
        "Resource": DEPLOY_OBJECTS,
        "Condition": {
            "Null": {
                "s3:x-amz-server-side-encryption": "false",
                "s3:x-amz-server-side-encryption-aws-kms-key-id": "true",
            }
        },
    },
    "DenyKmsKeyOtherThanProjectKey": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:PutObject",
        "Resource": DEPLOY_OBJECTS,
        "Condition": {
            "Null": {"s3:x-amz-server-side-encryption-aws-kms-key-id": "false"},
            "StringNotEquals": {"s3:x-amz-server-side-encryption-aws-kms-key-id": KEY},
        },
    },
    "DenyRuntimeRoleExceptBundlesRead": {
        "Effect": "Deny",
        "Principal": "*",
        "NotAction": ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"],
        "Resource": [DEPLOY_BUCKET_ARN, DEPLOY_OBJECTS],
        "Condition": RUNTIME_ONLY,
    },
    "DenyRuntimeRoleGetOutsideBundles": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:GetObject",
        "NotResource": {"Fn::Sub": "${DeployBucket.Arn}/bundles/*"},
        "Condition": RUNTIME_ONLY,
    },
    "DenyRuntimeRoleListOutsideBundles": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:ListBucket",
        "Resource": DEPLOY_BUCKET_ARN,
        "Condition": {**RUNTIME_ONLY, "StringNotLike": {"s3:prefix": "bundles/*"}},
    },
}


def _template() -> dict[str, Any]:
    return guard.load_template(TEMPLATE)


def _resources() -> dict[str, Any]:
    return _template()["Resources"]


def _props(name: str) -> dict[str, Any]:
    return _resources()[name]["Properties"]


def _by_sid(policy_resource: str) -> dict[str, dict[str, Any]]:
    document = _props(policy_resource)["PolicyDocument"]
    statements = document["Statement"]
    by_sid = {s["Sid"]: {k: v for k, v in s.items() if k != "Sid"} for s in statements}
    assert document["Version"] == "2012-10-17"
    assert len(by_sid) == len(statements), "duplicate Sid"
    return by_sid


def _imports(node: Any) -> list[str]:
    if isinstance(node, dict):
        found = [node["Fn::ImportValue"]] if "Fn::ImportValue" in node else []
        return found + [i for v in node.values() for i in _imports(v)]
    if isinstance(node, list):
        return [i for v in node for i in _imports(v)]
    return []


def test_exactly_the_audit_and_storage_resources() -> None:
    assert {name: r["Type"] for name, r in _resources().items()} == {
        "TrailBucket": "AWS::S3::Bucket",
        "TrailBucketPolicy": "AWS::S3::BucketPolicy",
        "Trail": "AWS::CloudTrail::Trail",
        "DeployBucket": "AWS::S3::Bucket",
        "DeployBucketPolicy": "AWS::S3::BucketPolicy",
        "FlowLogGroup": "AWS::Logs::LogGroup",
        "VpcFlowLog": "AWS::EC2::FlowLog",
    }


def test_buckets_and_log_group_are_retained_trail_and_flow_log_are_not() -> None:
    resources = _resources()
    for name in ("TrailBucket", "DeployBucket", "FlowLogGroup"):
        assert resources[name]["DeletionPolicy"] == "Retain", name
        assert resources[name]["UpdateReplacePolicy"] == "Retain", name
    for name in ("Trail", "VpcFlowLog", "TrailBucketPolicy", "DeployBucketPolicy"):
        assert "DeletionPolicy" not in resources[name], name
        assert "UpdateReplacePolicy" not in resources[name], name


def test_bucket_names_are_derived() -> None:
    assert _props("TrailBucket")["BucketName"] == {"Fn::Sub": "${ProjectName}-cloudtrail-${AWS::AccountId}"}
    assert _props("DeployBucket")["BucketName"] == {"Fn::Sub": "${ProjectName}-deploy-${AWS::AccountId}"}


def test_both_buckets_use_the_cmk_bucket_key_only_on_the_deploy_bucket() -> None:
    for name, bucket_key in (("TrailBucket", False), ("DeployBucket", True)):
        (rule,) = _props(name)["BucketEncryption"]["ServerSideEncryptionConfiguration"]
        assert rule == {
            "ServerSideEncryptionByDefault": {"SSEAlgorithm": "aws:kms", "KMSMasterKeyID": KEY},
            "BucketKeyEnabled": bucket_key,
        }, name


def test_both_buckets_block_public_access_version_and_enforce_ownership() -> None:
    for name in ("TrailBucket", "DeployBucket"):
        props = _props(name)
        assert props["PublicAccessBlockConfiguration"] == PUBLIC_ACCESS_BLOCK, name
        assert props["VersioningConfiguration"] == {"Status": "Enabled"}, name
        assert props["OwnershipControls"] == {"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]}, name


def test_trail_bucket_lifecycle_is_the_v1_rule_with_new_names() -> None:
    assert _props("TrailBucket")["LifecycleConfiguration"] == {
        "Rules": [
            {
                "Id": {"Fn::Sub": "${ProjectName}-cloudtrail-lifecycle"},
                "Status": "Enabled",
                "Prefix": {"Fn::Sub": "cloudtrail/${ProjectName}/"},
                "Transitions": [{"TransitionInDays": 90, "StorageClass": "GLACIER_IR"}],
                "ExpirationInDays": 365,
                "NoncurrentVersionExpiration": {"NoncurrentDays": 30},
            }
        ]
    }


def test_deploy_bucket_lifecycle_expires_only_old_versions_and_stale_uploads() -> None:
    assert _props("DeployBucket")["LifecycleConfiguration"] == {
        "Rules": [
            {
                "Id": {"Fn::Sub": "${ProjectName}-deploy-lifecycle"},
                "Status": "Enabled",
                "NoncurrentVersionExpiration": {"NoncurrentDays": 30},
                "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7},
            }
        ]
    }


def test_trail_bucket_policy_is_exactly_the_v1_policy_with_new_arns() -> None:
    assert _props("TrailBucketPolicy")["Bucket"] == {"Ref": "TrailBucket"}
    assert _by_sid("TrailBucketPolicy") == EXPECTED_TRAIL_BUCKET_POLICY


def test_deploy_bucket_policy_is_exactly_the_decided_denies() -> None:
    assert _props("DeployBucketPolicy")["Bucket"] == {"Ref": "DeployBucket"}
    assert _by_sid("DeployBucketPolicy") == EXPECTED_DEPLOY_BUCKET_POLICY


def test_principal_star_appears_only_in_deny_statements() -> None:
    for policy in ("TrailBucketPolicy", "DeployBucketPolicy"):
        for sid, statement in _by_sid(policy).items():
            if statement["Effect"] == "Allow":
                assert statement["Principal"] == {"Service": "cloudtrail.amazonaws.com"}, (policy, sid)
            else:
                assert statement["Principal"] == "*", (policy, sid)
    assert all(s["Effect"] == "Deny" for s in _by_sid("DeployBucketPolicy").values())


def test_trail_is_the_r6_trail_with_the_cmk_and_integrity_digests() -> None:
    trail = _resources()["Trail"]

    assert trail["DependsOn"] == "TrailBucketPolicy"
    assert trail["Properties"] == {
        "TrailName": {"Fn::Sub": "${ProjectName}-bedrock-trail"},
        "S3BucketName": {"Ref": "TrailBucket"},
        "S3KeyPrefix": {"Fn::Sub": "cloudtrail/${ProjectName}"},
        "KMSKeyId": KEY,
        "EnableLogFileValidation": True,
        "IncludeGlobalServiceEvents": True,
        "IsMultiRegionTrail": False,
        "IsLogging": True,
        "Tags": trail["Properties"]["Tags"],
    }


def test_trail_arn_is_the_one_the_key_policy_names() -> None:
    """R6-D2: the key grants CloudTrail only for this trail ARN."""
    key_text = KMS_TEMPLATE.read_text(encoding="utf-8")

    assert TRAIL_ARN["Fn::Sub"] in key_text
    prefix = _props("Trail")["S3KeyPrefix"]["Fn::Sub"]
    write = EXPECTED_TRAIL_BUCKET_POLICY["AWSCloudTrailWrite"]["Resource"]["Fn::Sub"]
    assert write.startswith("${TrailBucket.Arn}/" + prefix + "/AWSLogs/")
    lifecycle_prefix = _props("TrailBucket")["LifecycleConfiguration"]["Rules"][0]["Prefix"]["Fn::Sub"]
    assert lifecycle_prefix == prefix + "/"


def test_flow_log_group_is_the_r5_group_with_cmk_and_90_days() -> None:
    props = _props("FlowLogGroup")

    assert props["LogGroupName"] == {"Fn::Sub": "/${ProjectName}/vpc-flow-logs"}
    assert props["RetentionInDays"] == 90
    assert props["KmsKeyId"] == KEY
    assert "/${ProjectName}/vpc-flow-logs" in IAM_TEMPLATE.read_text(encoding="utf-8")
    assert "log-group:/${ProjectName}/*" in KMS_TEMPLATE.read_text(encoding="utf-8")


def test_one_flow_log_on_the_vpc_all_traffic_to_the_group() -> None:
    props = _props("VpcFlowLog")

    assert props == {
        "ResourceType": "VPC",
        "ResourceId": {"Fn::ImportValue": "proposal-orchestrator-network-VpcId"},
        "TrafficType": "ALL",
        "LogDestinationType": "cloud-watch-logs",
        "LogGroupName": {"Ref": "FlowLogGroup"},
        "DeliverLogsPermissionArn": {"Fn::ImportValue": "proposal-orchestrator-iam-FlowLogsRoleArn"},
        "MaxAggregationInterval": 600,
        "Tags": props["Tags"],
    }


def test_imports_are_exactly_the_exports_that_name_r7_as_consumer() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
    wanted = {
        output["export"]
        for stack in contract["stacks"]
        for output in stack["outputs"].values()
        if "R7" in output["consumers"]
    }

    assert set(_imports(_resources())) == wanted
    assert wanted == {
        "proposal-orchestrator-network-VpcId",
        "proposal-orchestrator-iam-RuntimeRoleArn",
        "proposal-orchestrator-iam-FlowLogsRoleArn",
        "proposal-orchestrator-kms-KeyArn",
    }


def test_no_literal_role_or_key_arn() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "runtime-role" not in text
    assert "flow-logs-role" not in text
    assert ":key/" not in text


def test_every_taggable_resource_carries_name_and_project_tags() -> None:
    for name, resource in _resources().items():
        if resource["Type"] in guard.UNTAGGABLE_TYPES:
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"]["Tags"]}
        assert set(tags) == {"Name", "project"}, name
        assert tags["project"] == {"Ref": "ProjectName"}, name


def test_no_event_selectors_and_no_invocation_logging_resource() -> None:
    assert "EventSelectors" not in _props("Trail")
    assert "AdvancedEventSelectors" not in _props("Trail")
    assert not any(r["Type"].startswith("AWS::Bedrock::") for r in _resources().values())


def test_outputs_are_the_contract_with_their_values() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
    (audit,) = [s for s in contract["stacks"] if s["key"] == "audit"]
    outputs = _template()["Outputs"]

    assert {k: v["Export"]["Name"] for k, v in outputs.items()} == {
        k: v["export"] for k, v in audit["outputs"].items()
    }
    assert outputs["TrailBucketName"]["Value"] == {"Ref": "TrailBucket"}
    assert outputs["DeployBucketName"]["Value"] == {"Ref": "DeployBucket"}
    assert outputs["TrailArn"]["Value"] == {"Fn::GetAtt": ["Trail", "Arn"]}
    assert outputs["FlowLogGroupName"]["Value"] == {"Ref": "FlowLogGroup"}
    assert outputs["FlowLogGroupArn"]["Value"] == {"Fn::GetAtt": ["FlowLogGroup", "Arn"]}
    assert outputs["FlowLogId"]["Value"] == {"Ref": "VpcFlowLog"}


def test_metadata_names_the_fill_decision() -> None:
    meta = _template()["Metadata"]["ProposalOrchestrator"]

    assert meta["Decision"] == "aws-redeployment-od6-stack-layout-r3_2026-10-22"
    assert meta["FillDecision"] == "aws-redeployment-r7-audit_2026-10-26"
    assert RECORD.exists()
