"""R3 — the parsed-template guard (``tools/aws_template_guard.py``).

Suggested in ``plans/aws_redeployment_r3_handoff_2026-10-22.md`` §2 and
approved by the operator on 2026-10-22: no Internet or NAT gateway or Elastic
IP (and, since R4, no ``AWS::EC2::Route``), no ``0.0.0.0/0``, the project tag on every taggable resource, no
"temporary" or "validation" in a name or description (R5), no Region literal
outside a parameter default (F9), no account literal, and a template small
enough for ``--template-body``.

Each check is shown to refuse a planted fixture and to pass the real
templates in ``deploy/aws/templates/``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import aws_template_guard as guard

TEMPLATES = Path("deploy") / "aws" / "templates"

HEADER = """\
AWSTemplateFormatVersion: "2010-09-09"
Description: fixture
Parameters:
  ProjectName:
    Type: String
    Default: proposal-orchestrator
  ExpectedRegion:
    Type: String
    Default: eu-north-1
Resources:
"""

CLEAN_RESOURCES = """\
  Vpc:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.60.0.0/24
      Tags:
        - Key: project
          Value: !Ref ProjectName
  HostEgress:
    Type: AWS::EC2::SecurityGroupEgress
    Properties:
      GroupId: !GetAtt HostSg.GroupId
      IpProtocol: tcp
      FromPort: 443
      ToPort: 443
      DestinationPrefixListId: !Ref S3PrefixListId
  Trail:
    Type: AWS::CloudTrail::Trail
    Properties:
      TrailName: !Sub "${ProjectName}-bedrock-trail"
      EnableLogFileValidation: true
      IsLogging: true
      S3BucketName: !Sub "${ProjectName}-cloudtrail-${AWS::AccountId}"
      Tags:
        - Key: project
          Value: proposal-orchestrator
"""

# check name -> resources block that must trip exactly that check
PLANTED = {
    "forbidden-type": """\
  Igw:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: project
          Value: proposal-orchestrator
""",
    "open-cidr": """\
  OpenIngress:
    Type: AWS::EC2::SecurityGroupIngress
    Properties:
      GroupId: !GetAtt HostSg.GroupId
      IpProtocol: tcp
      FromPort: 443
      ToPort: 443
      CidrIp: 0.0.0.0/0
""",
    "project-tag": """\
  Subnet:
    Type: AWS::EC2::Subnet
    Properties:
      CidrBlock: 10.60.0.0/25
      Tags:
        - Key: Name
          Value: private
""",
    "forbidden-word": """\
  Invoke:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      ManagedPolicyName: !Sub "${ProjectName}-validation-invoke"
      PolicyDocument:
        Statement:
          - Effect: Allow
            Action: sts:GetCallerIdentity
            Resource: "*"
""",
    "region-literal": """\
  Profile:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      Description: invoke policy
      PolicyDocument:
        Statement:
          - Effect: Allow
            Action: bedrock:InvokeModel
            Resource: !Sub "arn:aws:bedrock:eu-west-1::foundation-model/x"
""",
    "account-literal": """\
  Key:
    Type: AWS::KMS::Key
    Properties:
      KeyPolicy:
        Statement:
          - Effect: Allow
            Principal:
              AWS: arn:aws:iam::123456789012:root
            Action: kms:*
            Resource: "*"
      Tags:
        - Key: project
          Value: proposal-orchestrator
""",
}


def _write(tmp_path: Path, body: str, name: str = "t.yaml") -> Path:
    path = tmp_path / name
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def test_loader_understands_short_form_intrinsics(tmp_path: Path) -> None:
    template = guard.load_template(_write(tmp_path, CLEAN_RESOURCES))
    vpc_tag = template["Resources"]["Vpc"]["Properties"]["Tags"][0]
    egress = template["Resources"]["HostEgress"]["Properties"]

    assert vpc_tag == {"Key": "project", "Value": {"Ref": "ProjectName"}}
    assert egress["GroupId"] == {"Fn::GetAtt": ["HostSg", "GroupId"]}
    assert template["Resources"]["Trail"]["Properties"]["TrailName"] == {"Fn::Sub": "${ProjectName}-bedrock-trail"}


def test_clean_fixture_passes(tmp_path: Path) -> None:
    """Includes a parameter-default Region, EnableLogFileValidation and an untaggable type."""
    assert guard.check_template(_write(tmp_path, CLEAN_RESOURCES)) == []


@pytest.mark.parametrize("check", sorted(PLANTED))
def test_each_check_refuses_its_planted_fixture(tmp_path: Path, check: str) -> None:
    path = _write(tmp_path, CLEAN_RESOURCES + PLANTED[check])

    assert {f.check for f in guard.check_template(path)} == {check}
    assert guard.main([str(path)]) == 1


def test_ipv6_open_cidr_is_refused(tmp_path: Path) -> None:
    body = PLANTED["open-cidr"].replace("CidrIp: 0.0.0.0/0", 'CidrIpv6: "::/0"')

    assert {f.check for f in guard.check_template(_write(tmp_path, body))} == {"open-cidr"}


def test_route_resource_is_refused_even_to_a_prefix_list(tmp_path: Path) -> None:
    """R4 (R4-D4): no template writes a route; the S3 gateway endpoint adds its own."""
    body = """\
  PrefixListRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTable
      DestinationPrefixListId: !Ref S3PrefixListId
      VpcEndpointId: !Ref S3GatewayEndpoint
"""

    assert {f.check for f in guard.check_template(_write(tmp_path, CLEAN_RESOURCES + body))} == {"forbidden-type"}


def test_iam_managed_policy_and_instance_profile_take_no_tags(tmp_path: Path) -> None:
    """R5 (F-R5-3): both types have no Tags property; an IAM role does and must carry the tag."""
    body = """\
  Boundary:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      ManagedPolicyName: !Sub "${ProjectName}-boundary"
      PolicyDocument:
        Statement:
          - Effect: Allow
            Action: sts:GetCallerIdentity
            Resource: "*"
  Profile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Roles:
        - !Ref Role
"""
    role = """\
  Role:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument: {}
"""

    assert {"AWS::IAM::ManagedPolicy", "AWS::IAM::InstanceProfile"} <= guard.UNTAGGABLE_TYPES
    assert "AWS::IAM::Role" not in guard.UNTAGGABLE_TYPES
    assert guard.check_template(_write(tmp_path, CLEAN_RESOURCES + body)) == []
    findings = guard.check_template(_write(tmp_path, CLEAN_RESOURCES + body + role))
    assert [(f.check, f.where) for f in findings] == [("project-tag", "Resources.Role")]


def test_temporary_in_a_description_is_refused(tmp_path: Path) -> None:
    body = PLANTED["region-literal"].replace("Description: invoke policy", "Description: Temporary invoke grant")
    body = body.replace("eu-west-1", "${AWS::Region}")

    assert {f.check for f in guard.check_template(_write(tmp_path, body))} == {"forbidden-word"}


def test_oversized_template_is_refused(tmp_path: Path) -> None:
    padding = "# " + "x" * 100 + "\n"
    path = _write(tmp_path, CLEAN_RESOURCES + padding * 520)

    assert {f.check for f in guard.check_template(path)} == {"size"}


def test_every_check_is_planted() -> None:
    assert set(PLANTED) | {"size"} == {
        "forbidden-type",
        "open-cidr",
        "project-tag",
        "forbidden-word",
        "region-literal",
        "account-literal",
        "size",
    }


# --- the real templates ---------------------------------------------------------


def test_real_templates_are_clean(capsys: pytest.CaptureFixture[str]) -> None:
    files = guard.template_files([TEMPLATES])

    assert len(files) == 6
    assert [f.describe() for file in files for f in guard.check_template(file)] == []
    assert guard.main([str(TEMPLATES)]) == 0
    assert "CLEAN: 6 template(s)" in capsys.readouterr().out


def test_missing_or_empty_path_is_an_error(tmp_path: Path) -> None:
    assert guard.main([str(tmp_path / "nope")]) == 2
    assert guard.main([str(tmp_path)]) == 2
