"""R4 — the filled network template (``deploy/aws/templates/10-network.yaml``).

Acceptance, from ``plans/aws_redeployment_tickets.md`` R4, the R4 handoff
(``plans/aws_redeployment_r4_handoff_2026-10-23.md`` §3, §4) and the
operator's answers of 2026-10-24 (decision record
``aws-redeployment-r4-network_2026-10-24``):

- a dedicated VPC with both DNS attributes on (OD3, PL-8); one private subnet
  in the parameter zone with no public IP on launch (OD4);
- one route table, associated with that subnet, and **no** ``AWS::EC2::Route``
  resource: the S3 gateway endpoint adds the one prefix-list route (DC-06);
- host security group: egress TCP 443 to the S3 prefix list (inline) and to
  the endpoint security group (standalone), nothing else, no ingress (DC-07);
- endpoint security group: ingress TCP 443 from the host security group only;
  the one egress entry is the loopback placeholder that replaces the AWS
  default allow-all egress (DC-03, R4-D1);
- S3 gateway endpoint on that route table whose policy admits read-only
  actions on this account's deploy bucket, for principals of this account
  only (F7, DC-05, R4-D3);
- ``Name`` and ``project`` tags on every taggable resource; exactly the
  contract outputs (checked in detail by ``tests/test_aws_iac_contract.py``).

The guard (``tools/aws_template_guard.py``) and cfn-lint cover the generic
rules; this file pins the network stack's shape so a later edit cannot widen
it unnoticed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools import aws_template_guard as guard

TEMPLATE = Path("deploy") / "aws" / "templates" / "10-network.yaml"
CONTRACT = Path("deploy") / "aws" / "outputs_contract.json"
PARAMETERS = Path("deploy") / "aws" / "parameters" / "network.json"

EXPECTED_RESOURCES = {
    "Vpc": "AWS::EC2::VPC",
    "PrivateSubnet": "AWS::EC2::Subnet",
    "PrivateRouteTable": "AWS::EC2::RouteTable",
    "PrivateSubnetRouteTableAssociation": "AWS::EC2::SubnetRouteTableAssociation",
    "HostSecurityGroup": "AWS::EC2::SecurityGroup",
    "EndpointSecurityGroup": "AWS::EC2::SecurityGroup",
    "HostToEndpointEgress": "AWS::EC2::SecurityGroupEgress",
    "S3GatewayEndpoint": "AWS::EC2::VPCEndpoint",
}
READ_ONLY_ACTIONS = {"s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"}
LOOPBACK_PLACEHOLDER = {"IpProtocol": "-1", "CidrIp": "127.0.0.1/32"}
HTTPS = {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443}
ACCOUNT = {"Ref": "AWS::AccountId"}


@pytest.fixture(scope="module")
def template() -> dict[str, Any]:
    return guard.load_template(TEMPLATE)


@pytest.fixture(scope="module")
def resources(template: dict[str, Any]) -> dict[str, Any]:
    return template["Resources"]


def _props(resources: dict[str, Any], logical_id: str) -> dict[str, Any]:
    return resources[logical_id]["Properties"]


def _rule_core(rule: dict[str, Any]) -> dict[str, Any]:
    """A security-group rule without its Description, for comparison."""
    return {k: v for k, v in rule.items() if k != "Description"}


def _group_ref(logical_id: str) -> list[Any]:
    """The two ways a template may point at a security group's id."""
    return [{"Ref": logical_id}, {"Fn::GetAtt": [logical_id, "GroupId"]}]


# --- shape ----------------------------------------------------------------------


def test_exactly_the_expected_resources(resources: dict[str, Any]) -> None:
    assert {k: v["Type"] for k, v in resources.items()} == EXPECTED_RESOURCES
    assert "SkeletonPlaceholder" not in resources


def test_no_route_resource_and_no_gateway(resources: dict[str, Any]) -> None:
    types = {v["Type"] for v in resources.values()}

    assert "AWS::EC2::Route" not in types
    assert not types & guard.FORBIDDEN_RESOURCE_TYPES
    assert guard.check_template(TEMPLATE) == []


def test_every_taggable_resource_has_name_and_project_tags(resources: dict[str, Any]) -> None:
    for logical_id, resource in resources.items():
        if resource["Type"] in guard.UNTAGGABLE_TYPES:
            assert "Tags" not in resource["Properties"], logical_id
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"]["Tags"]}
        assert tags["project"] == {"Ref": "ProjectName"}, logical_id
        name = tags["Name"]
        assert isinstance(name, dict) and list(name) == ["Fn::Sub"], logical_id
        assert name["Fn::Sub"].startswith("${ProjectName}-"), logical_id


# --- VPC, subnet, route table ---------------------------------------------------


def test_vpc_is_dedicated_with_both_dns_attributes_on(resources: dict[str, Any]) -> None:
    vpc = _props(resources, "Vpc")

    assert vpc["CidrBlock"] == {"Ref": "VpcCidr"}
    assert vpc["EnableDnsSupport"] is True, "PL-8"
    assert vpc["EnableDnsHostnames"] is True, "PL-8"
    assert vpc.get("InstanceTenancy", "default") == "default"


def test_one_private_subnet_in_the_parameter_zone(resources: dict[str, Any]) -> None:
    subnet = _props(resources, "PrivateSubnet")

    assert subnet["VpcId"] == {"Ref": "Vpc"}
    assert subnet["CidrBlock"] == {"Ref": "PrivateSubnetCidr"}
    assert subnet["AvailabilityZone"] == {"Ref": "AvailabilityZone"}, "OD4"
    assert subnet["MapPublicIpOnLaunch"] is False
    assert "Ipv6CidrBlock" not in subnet and "AssignIpv6AddressOnCreation" not in subnet


def test_route_table_belongs_to_the_vpc_and_the_subnet(resources: dict[str, Any]) -> None:
    assert _props(resources, "PrivateRouteTable")["VpcId"] == {"Ref": "Vpc"}
    association = _props(resources, "PrivateSubnetRouteTableAssociation")
    assert association == {"SubnetId": {"Ref": "PrivateSubnet"}, "RouteTableId": {"Ref": "PrivateRouteTable"}}


def test_subnet_cidr_default_lies_inside_the_vpc_default(template: dict[str, Any]) -> None:
    import ipaddress

    params = template["Parameters"]
    vpc = ipaddress.ip_network(params["VpcCidr"]["Default"])
    subnet = ipaddress.ip_network(params["PrivateSubnetCidr"]["Default"])

    assert vpc.is_private and subnet.subnet_of(vpc)


# --- security groups (DC-03, DC-07 halves) --------------------------------------


def test_host_security_group_egress_is_443_to_prefix_list_and_endpoint_group_only(
    resources: dict[str, Any],
) -> None:
    host = _props(resources, "HostSecurityGroup")
    assert host["VpcId"] == {"Ref": "Vpc"}
    assert "SecurityGroupIngress" not in host, "the host accepts nothing inbound"

    inline = [_rule_core(r) for r in host["SecurityGroupEgress"]]
    assert inline == [{**HTTPS, "DestinationPrefixListId": {"Ref": "S3PrefixListId"}}]

    standalone = [
        _rule_core(v["Properties"])
        for v in resources.values()
        if v["Type"] == "AWS::EC2::SecurityGroupEgress" and v["Properties"]["GroupId"] in _group_ref("HostSecurityGroup")
    ]
    assert len(standalone) == 1
    (rule,) = standalone
    assert rule["DestinationSecurityGroupId"] in _group_ref("EndpointSecurityGroup")
    assert {k: v for k, v in rule.items() if k not in ("GroupId", "DestinationSecurityGroupId")} == HTTPS

    assert not any(
        v["Type"] == "AWS::EC2::SecurityGroupIngress" and v["Properties"]["GroupId"] in _group_ref("HostSecurityGroup")
        for v in resources.values()
    )


def test_endpoint_security_group_ingress_from_host_only_and_placeholder_egress(
    resources: dict[str, Any],
) -> None:
    endpoint = _props(resources, "EndpointSecurityGroup")
    assert endpoint["VpcId"] == {"Ref": "Vpc"}

    ingress = [_rule_core(r) for r in endpoint["SecurityGroupIngress"]]
    assert len(ingress) == 1
    assert ingress[0]["SourceSecurityGroupId"] in _group_ref("HostSecurityGroup")
    assert {k: v for k, v in ingress[0].items() if k != "SourceSecurityGroupId"} == HTTPS

    egress = [_rule_core(r) for r in endpoint["SecurityGroupEgress"]]
    assert egress == [LOOPBACK_PLACEHOLDER], "R4-D1: the loopback placeholder replaces the default egress"
    assert "Placeholder" in endpoint["SecurityGroupEgress"][0]["Description"]

    assert not any(
        v["Type"] in ("AWS::EC2::SecurityGroupEgress", "AWS::EC2::SecurityGroupIngress")
        and v["Properties"]["GroupId"] in _group_ref("EndpointSecurityGroup")
        for v in resources.values()
    ), "no standalone rule widens the endpoint security group"


def test_no_security_group_rule_names_a_cidr_but_the_placeholder(resources: dict[str, Any]) -> None:
    rules: list[dict[str, Any]] = []
    for v in resources.values():
        if v["Type"] == "AWS::EC2::SecurityGroup":
            rules += v["Properties"].get("SecurityGroupIngress", [])
            rules += v["Properties"].get("SecurityGroupEgress", [])
        elif v["Type"] in ("AWS::EC2::SecurityGroupEgress", "AWS::EC2::SecurityGroupIngress"):
            rules.append(v["Properties"])
    cidr_rules = [r for r in rules if "CidrIp" in r or "CidrIpv6" in r]

    assert [_rule_core(r) for r in cidr_rules] == [LOOPBACK_PLACEHOLDER]
    assert all(r["IpProtocol"] == "tcp" for r in rules if r is not cidr_rules[0])


# --- S3 gateway endpoint (F7, DC-05 half) ---------------------------------------


def test_s3_gateway_endpoint_sits_on_the_private_route_table(resources: dict[str, Any]) -> None:
    endpoint = _props(resources, "S3GatewayEndpoint")

    assert endpoint["VpcId"] == {"Ref": "Vpc"}
    assert endpoint["VpcEndpointType"] == "Gateway"
    assert endpoint["ServiceName"] == {"Fn::Sub": "com.amazonaws.${AWS::Region}.s3"}
    assert endpoint["RouteTableIds"] == [{"Ref": "PrivateRouteTable"}]
    for key in ("SubnetIds", "SecurityGroupIds", "PrivateDnsEnabled", "DnsOptions"):
        assert key not in endpoint, f"{key} belongs to interface endpoints"


def test_s3_endpoint_policy_is_read_only_on_the_deploy_bucket_of_this_account(
    resources: dict[str, Any],
) -> None:
    policy = _props(resources, "S3GatewayEndpoint")["PolicyDocument"]
    assert policy["Version"] == "2012-10-17"
    (statement,) = policy["Statement"]

    assert statement["Effect"] == "Allow"
    assert statement["Principal"] == "*"
    assert set(statement["Action"]) == READ_ONLY_ACTIONS, "R4-D3: read-only"
    assert not any(a.split(":")[1].startswith(("Put", "Delete", "Create")) for a in statement["Action"])

    resources_ = statement["Resource"]
    assert len(resources_) == 2
    for arn in resources_:
        assert list(arn) == ["Fn::Sub"], arn
        text = arn["Fn::Sub"]
        assert text.startswith("arn:${AWS::Partition}:s3:::${ProjectName}-deploy-${AWS::AccountId}")
        assert text.endswith(("${AWS::AccountId}", "${AWS::AccountId}/*")), "every bucket carries this account's id"
    assert {a["Fn::Sub"].rsplit("${AWS::AccountId}", 1)[1] for a in resources_} == {"", "/*"}

    assert statement["Condition"] == {"StringEquals": {"aws:ResourceAccount": ACCOUNT, "aws:PrincipalAccount": ACCOUNT}}


def test_s3_endpoint_policy_names_no_foreign_bucket(resources: dict[str, Any]) -> None:
    """OD9 added no AL2023 repository bucket; the trail and SSM buckets stay out (R4-D3)."""
    policy = json.dumps(_props(resources, "S3GatewayEndpoint")["PolicyDocument"])

    for fragment in ("al2023", "amazonlinux", "cloudtrail", "aws-ssm", "amazon-ssm", "birdwatcher", "patch-baseline"):
        assert fragment not in policy.lower(), fragment


# --- outputs and parameters -----------------------------------------------------


def test_outputs_point_at_the_right_resources(template: dict[str, Any]) -> None:
    outputs = {k: v["Value"] for k, v in template["Outputs"].items()}

    assert outputs == {
        "VpcId": {"Ref": "Vpc"},
        "PrivateSubnetId": {"Ref": "PrivateSubnet"},
        "PrivateSubnetAz": {"Fn::GetAtt": ["PrivateSubnet", "AvailabilityZone"]},
        "PrivateRouteTableId": {"Ref": "PrivateRouteTable"},
        "HostSecurityGroupId": {"Fn::GetAtt": ["HostSecurityGroup", "GroupId"]},
        "EndpointSecurityGroupId": {"Fn::GetAtt": ["EndpointSecurityGroup", "GroupId"]},
        "S3GatewayEndpointId": {"Ref": "S3GatewayEndpoint"},
    }
    contract = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
    (network,) = [s for s in contract["stacks"] if s["key"] == "network"]
    assert set(outputs) == set(network["outputs"])


def test_parameter_file_supplies_zone_and_prefix_list(template: dict[str, Any]) -> None:
    values = {e["ParameterKey"]: e["ParameterValue"] for e in json.loads(PARAMETERS.read_text(encoding="utf-8-sig"))}
    without_default = {k for k, v in template["Parameters"].items() if "Default" not in v}

    assert without_default <= set(values)
    assert values["S3PrefixListId"].startswith("pl-")
    assert values["AvailabilityZone"].startswith(values["ExpectedRegion"])
