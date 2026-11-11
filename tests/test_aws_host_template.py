"""R11 — the filled endpoints-and-host template (``deploy/aws/templates/90-host.yaml``).

Acceptance, from ``plans/aws_redeployment_tickets.md`` R11, the handoff
(``plans/aws_redeployment_handoff_2026-10-21.md`` §4 F1, F2, F7; §6 R11; §7)
and the decision records OD2 (one hardened runtime role), OD4 (one zone),
OD5 (per-session stack), OD6-r3 (stack layout, imports, outputs contract),
OD7-resources (model lists) and OD9-r1 (AL2023 x86_64, c7i-flex.large):

- exactly six interface endpoints (``bedrock-runtime``, ``sts``,
  ``secretsmanager``, ``ssm``, ``ssmmessages``, ``ec2messages``) and one
  host, nothing else: no gateway, route, Elastic IP, security group or
  Bedrock logging resource (the base stacks own the network; invocation
  logging stays off);
- every endpoint is of type ``Interface``, in the one imported private
  subnet, behind the imported endpoint security group, with private DNS on
  (DC-01, DC-02, DC-03 attached, DC-05);
- only the ``bedrock-runtime`` endpoint carries a policy: invoke actions
  only, only for the imported runtime role, only on the OD7 inference
  profiles and their routed foundation models (DC-04, F2);
- the host: AL2023 from the public SSM parameter, the imported runtime
  instance profile (DC-14, F1), one network interface in the private subnet
  with the imported host security group and no public IP, IMDSv2 required
  with hop limit 1, an encrypted gp3 root volume deleted on termination, no
  key pair and no user data; created after the six endpoints;
- every id comes from an ``Fn::ImportValue`` of a base-stack export, never a
  literal; outputs are exactly the contract's host outputs, without exports.

The guard (``tools/aws_template_guard.py``) and cfn-lint cover the generic
rules (no ``0.0.0.0/0``, no Region or account literal, project tags); this file
pins the host stack's shape so a later edit cannot widen it unnoticed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools import aws_template_guard as guard

TEMPLATE = Path("deploy") / "aws" / "templates" / "90-host.yaml"
CONTRACT = Path("deploy") / "aws" / "outputs_contract.json"
PARAMETERS = Path("deploy") / "aws" / "parameters" / "host.json"

ENDPOINTS = {
    "BedrockRuntimeEndpoint": "bedrock-runtime",
    "StsEndpoint": "sts",
    "SecretsManagerEndpoint": "secretsmanager",
    "SsmEndpoint": "ssm",
    "SsmMessagesEndpoint": "ssmmessages",
    "Ec2MessagesEndpoint": "ec2messages",
}
EXPECTED_RESOURCES = {**{name: "AWS::EC2::VPCEndpoint" for name in ENDPOINTS}, "Host": "AWS::EC2::Instance"}

EXPECTED_OUTPUTS = {
    "BedrockRuntimeEndpointId": "BedrockRuntimeEndpoint",
    "StsEndpointId": "StsEndpoint",
    "SecretsManagerEndpointId": "SecretsManagerEndpoint",
    "SsmEndpointId": "SsmEndpoint",
    "SsmMessagesEndpointId": "SsmMessagesEndpoint",
    "Ec2MessagesEndpointId": "Ec2MessagesEndpoint",
    "InstanceId": "Host",
}


def _imp(name: str) -> dict[str, str]:
    return {"Fn::ImportValue": f"proposal-orchestrator-{name}"}


VPC = _imp("network-VpcId")
SUBNET = _imp("network-PrivateSubnetId")
ENDPOINT_SG = _imp("network-EndpointSecurityGroupId")
HOST_SG = _imp("network-HostSecurityGroupId")
RUNTIME_ROLE = _imp("iam-RuntimeRoleArn")
INSTANCE_PROFILE = _imp("iam-InstanceProfileName")

INVOKE_ACTIONS = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
EXPECTED_BEDROCK_POLICY: dict[str, dict[str, Any]] = {
    "RuntimeRoleInvokesOd7Profiles": {
        "Effect": "Allow",
        "Principal": "*",
        "Action": INVOKE_ACTIONS,
        "Resource": {"Ref": "InferenceProfileArns"},
        "Condition": {"ArnEquals": {"aws:PrincipalArn": RUNTIME_ROLE}},
    },
    "RuntimeRoleInvokesRoutedModels": {
        "Effect": "Allow",
        "Principal": "*",
        "Action": INVOKE_ACTIONS,
        "Resource": {"Ref": "FoundationModelArns"},
        "Condition": {"ArnEquals": {"aws:PrincipalArn": RUNTIME_ROLE}},
    },
}

# The one import the contract does not yet list R11 as a consumer of:
# AWS::EC2::VPCEndpoint requires VpcId (cfn-lint schema: required ["VpcId"]).
IMPORT_OUTSIDE_R11_CONSUMERS = {"proposal-orchestrator-network-VpcId"}


@pytest.fixture(scope="module")
def template() -> dict[str, Any]:
    return guard.load_template(TEMPLATE)


@pytest.fixture(scope="module")
def resources(template: dict[str, Any]) -> dict[str, Any]:
    return template["Resources"]


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8-sig"))


def _props(resources: dict[str, Any], logical_id: str) -> dict[str, Any]:
    return resources[logical_id]["Properties"]


def _imports(node: Any) -> list[str]:
    if isinstance(node, dict):
        found = [node["Fn::ImportValue"]] if "Fn::ImportValue" in node else []
        return found + [i for v in node.values() for i in _imports(v)]
    if isinstance(node, list):
        return [i for v in node for i in _imports(v)]
    return []


def _strings(node: Any) -> list[str]:
    if isinstance(node, dict):
        return [s for k, v in node.items() for s in [str(k), *_strings(v)]]
    if isinstance(node, list):
        return [s for v in node for s in _strings(v)]
    return [str(node)] if node is not None else []


# --- shape ---------------------------------------------------------------------


def test_exactly_six_interface_endpoints_and_one_host(resources: dict[str, Any]) -> None:
    assert {name: r["Type"] for name, r in resources.items()} == EXPECTED_RESOURCES
    assert "SkeletonPlaceholder" not in resources


def test_no_internet_path_and_no_invocation_logging(template: dict[str, Any]) -> None:
    """Handoff §7: no IGW, NAT, EIP or route; Bedrock invocation logging stays off."""
    types = {r["Type"] for r in template["Resources"].values()}
    assert not types & guard.FORBIDDEN_RESOURCE_TYPES
    assert not any(t.startswith("AWS::Bedrock::") or t.startswith("AWS::Logs::") for t in types)
    text = " ".join(_strings(template)).lower()
    for forbidden in ("0.0.0.0/0", "::/0", "invocationlogging", "loggingconfig"):
        assert forbidden not in text


def test_template_passes_the_guard() -> None:
    assert [f.describe() for f in guard.check_template(TEMPLATE)] == []


# --- endpoints -------------------------------------------------------------------


@pytest.mark.parametrize("logical_id", sorted(ENDPOINTS))
def test_each_endpoint_is_private_dns_interface_in_the_one_subnet(
    resources: dict[str, Any], logical_id: str
) -> None:
    props = _props(resources, logical_id)

    assert props["VpcEndpointType"] == "Interface"
    assert props["ServiceName"] == {"Fn::Sub": f"com.amazonaws.${{AWS::Region}}.{ENDPOINTS[logical_id]}"}
    assert props["VpcId"] == VPC
    assert props["SubnetIds"] == [SUBNET]  # OD4: one zone, one subnet
    assert props["SecurityGroupIds"] == [ENDPOINT_SG]  # DC-03 attached
    assert props["PrivateDnsEnabled"] is True  # DC-02
    assert "RouteTableIds" not in props
    tags = {t["Key"]: t["Value"] for t in props["Tags"]}
    assert tags["project"] == {"Ref": "ProjectName"}
    assert tags["Name"] == {"Fn::Sub": f"${{ProjectName}}-{ENDPOINTS[logical_id]}-endpoint"}


def test_only_the_bedrock_endpoint_carries_a_policy(resources: dict[str, Any]) -> None:
    with_policy = {name for name in ENDPOINTS if "PolicyDocument" in _props(resources, name)}
    assert with_policy == {"BedrockRuntimeEndpoint"}


def test_bedrock_endpoint_policy_is_runtime_role_invoke_on_od7_only(resources: dict[str, Any]) -> None:
    """DC-04, F2: the runtime role (OD2 a), invoke only, the OD7 lists only."""
    document = _props(resources, "BedrockRuntimeEndpoint")["PolicyDocument"]
    statements = document["Statement"]
    by_sid = {s["Sid"]: {k: v for k, v in s.items() if k != "Sid"} for s in statements}

    assert document["Version"] == "2012-10-17"
    assert len(by_sid) == len(statements)
    assert by_sid == EXPECTED_BEDROCK_POLICY
    assert all(s["Effect"] == "Allow" for s in statements)
    assert not any("NotAction" in s or "NotResource" in s or "NotPrincipal" in s for s in statements)


def test_bedrock_endpoint_lists_are_the_r5_invoke_lists(template: dict[str, Any]) -> None:
    """The endpoint admits the same parameters R5's invoke policy names (F-R5-2)."""
    iam = guard.load_template(Path("deploy") / "aws" / "templates" / "20-iam.yaml")
    invoke = iam["Resources"]["BedrockInvokePolicy"]["Properties"]["PolicyDocument"]["Statement"]

    assert [s["Resource"] for s in invoke] == [
        s["Resource"] for s in template["Resources"]["BedrockRuntimeEndpoint"]["Properties"]["PolicyDocument"]["Statement"]
    ]
    assert template["Parameters"]["InferenceProfileArns"]["Type"] == "CommaDelimitedList"
    assert template["Parameters"]["FoundationModelArns"]["Type"] == "CommaDelimitedList"


# --- host ---------------------------------------------------------------------------


def test_host_image_size_and_profile(template: dict[str, Any], resources: dict[str, Any]) -> None:
    props = _props(resources, "Host")
    params = template["Parameters"]

    assert props["ImageId"] == {"Ref": "LatestAmiId"}
    assert params["LatestAmiId"]["Type"] == "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>"
    assert params["LatestAmiId"]["Default"] == "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
    assert props["InstanceType"] == {"Ref": "InstanceType"}
    assert params["InstanceType"]["Default"] == "c7i-flex.large"  # OD9-r1
    # t3.medium is not Free Tier eligible (R11 step 06); t3.micro stays for a smoke run.
    assert params["InstanceType"]["AllowedValues"] == ["c7i-flex.large", "t3.micro"]
    assert props["IamInstanceProfile"] == INSTANCE_PROFILE  # DC-14, F1


def test_host_has_one_private_interface_and_no_public_ip(resources: dict[str, Any]) -> None:
    props = _props(resources, "Host")

    assert props["NetworkInterfaces"] == [
        {
            "DeviceIndex": "0",
            "SubnetId": SUBNET,
            "GroupSet": [HOST_SG],  # DC-07 attached
            "AssociatePublicIpAddress": False,
            "DeleteOnTermination": True,
        }
    ]
    for key in ("SubnetId", "SecurityGroupIds", "SecurityGroups", "AvailabilityZone", "Ipv6AddressCount",
                "Ipv6Addresses"):
        assert key not in props, key


def test_host_requires_imdsv2_with_hop_limit_one(resources: dict[str, Any]) -> None:
    assert _props(resources, "Host")["MetadataOptions"] == {
        "HttpEndpoint": "enabled",
        "HttpTokens": "required",
        "HttpPutResponseHopLimit": 1,
        "HttpProtocolIpv6": "disabled",
        "InstanceMetadataTags": "disabled",
    }


def test_host_root_volume_is_encrypted_gp3_deleted_on_termination(resources: dict[str, Any]) -> None:
    props = _props(resources, "Host")

    assert props["BlockDeviceMappings"] == [
        {"DeviceName": "/dev/xvda", "Ebs": {"VolumeType": "gp3", "Encrypted": True, "DeleteOnTermination": True}}
    ]
    assert "Volumes" not in props
    assert props["PropagateTagsToVolumeOnCreation"] is True


def test_host_has_no_key_pair_no_user_data_and_no_extras(resources: dict[str, Any]) -> None:
    props = _props(resources, "Host")

    for key in ("KeyName", "UserData", "LaunchTemplate", "SsmAssociations", "HibernationOptions",
                "SourceDestCheck", "ElasticGpuSpecifications", "PlacementGroupName"):
        assert key not in props, key
    # CPU credits are a T-instance setting: standard on t3, absent on c7i-flex (OD9-r1).
    assert props["CreditSpecification"] == {
        "Fn::If": ["IsBurstable", {"CPUCredits": "standard"}, {"Ref": "AWS::NoValue"}]
    }
    assert props["Monitoring"] is False
    assert props["DisableApiTermination"] is False
    tags = {t["Key"]: t["Value"] for t in props["Tags"]}
    assert tags == {"Name": {"Fn::Sub": "${ProjectName}-host"}, "project": {"Ref": "ProjectName"}}


def test_host_is_created_after_the_six_endpoints(resources: dict[str, Any]) -> None:
    assert sorted(resources["Host"]["DependsOn"]) == sorted(ENDPOINTS)


# --- imports and outputs -------------------------------------------------------------


def test_every_id_is_imported_from_a_base_export(template: dict[str, Any], contract: dict[str, Any]) -> None:
    exports = {o["export"] for s in contract["stacks"] if s["exports"] for o in s["outputs"].values()}
    imported = set(_imports(template["Resources"]))

    assert imported <= exports
    assert imported == {
        "proposal-orchestrator-network-VpcId",
        "proposal-orchestrator-network-PrivateSubnetId",
        "proposal-orchestrator-network-EndpointSecurityGroupId",
        "proposal-orchestrator-network-HostSecurityGroupId",
        "proposal-orchestrator-iam-RuntimeRoleArn",
        "proposal-orchestrator-iam-InstanceProfileName",
    }


def test_imports_are_r11_consumers_except_the_vpc(template: dict[str, Any], contract: dict[str, Any]) -> None:
    r11 = {o["export"] for s in contract["stacks"] if s["exports"] for o in s["outputs"].values()
           if "R11" in o["consumers"]}
    imported = set(_imports(template["Resources"]))

    assert imported - r11 == IMPORT_OUTSIDE_R11_CONSUMERS
    # The other R11 consumers are read by the step sheet from the outputs files:
    # PrivateSubnetAz, InstanceProfileArn, SecretArn.
    assert r11 - imported == {
        "proposal-orchestrator-network-PrivateSubnetAz",
        "proposal-orchestrator-iam-InstanceProfileArn",
        "proposal-orchestrator-secret-SecretArn",
    }


def test_no_literal_ids(template: dict[str, Any]) -> None:
    text = " ".join(_strings(template["Resources"]))
    for prefix in ("vpc-", "subnet-", "sg-", "vpce-", "i-0", "ami-0", "arn:aws:"):
        assert prefix not in text, prefix


def test_outputs_are_the_contract_without_exports(template: dict[str, Any], contract: dict[str, Any]) -> None:
    (host,) = [s for s in contract["stacks"] if s["key"] == "host"]
    outputs = template["Outputs"]

    assert set(outputs) == set(host["outputs"]) == set(EXPECTED_OUTPUTS)
    for name, logical_id in EXPECTED_OUTPUTS.items():
        assert outputs[name]["Value"] == {"Ref": logical_id}
        assert "Export" not in outputs[name]


def test_parameter_file_sets_exactly_the_required_parameters(template: dict[str, Any]) -> None:
    values = {p["ParameterKey"] for p in json.loads(PARAMETERS.read_text(encoding="utf-8-sig"))}
    required = {name for name, spec in template["Parameters"].items() if "Default" not in spec}

    assert required == {"ExpectedAccountId", "InferenceProfileArns", "FoundationModelArns"}
    assert required <= values
    assert values - required <= {"ExpectedRegion"}  # defaults are set only to state them


def test_cpu_credits_are_set_only_for_a_burstable_type(template: dict[str, Any]) -> None:
    # The condition reads the family before the first dot: "t3" for t3.micro, "c7i-flex" for c7i-flex.large.
    assert template["Conditions"]["IsBurstable"] == {
        "Fn::Equals": [{"Fn::Select": [0, {"Fn::Split": [".", {"Ref": "InstanceType"}]}]}, "t3"]
    }
    for allowed in template["Parameters"]["InstanceType"]["AllowedValues"]:
        assert (allowed.split(".")[0] == "t3") == allowed.startswith("t3."), allowed
