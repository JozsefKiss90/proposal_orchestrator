"""R3 — the IaC skeleton, its parameter files and the outputs contract.

Acceptance, from ``plans/aws_redeployment_tickets.md`` R3 and the operator's
answers of 2026-10-22 (decision record
``aws-redeployment-od6-stack-layout-r3_2026-10-22``):

- six stacks in deploy order (network, iam, kms, audit, secret: base, with
  exports; host: per session, no exports), one template and one parameter
  file each;
- every template guards its target with ``ExpectedAccountId`` and
  ``ExpectedRegion`` rules and carries ``ProjectName``;
- "The stack outputs are named": every output a later ticket or the R12a
  collector reads is in ``deploy/aws/outputs_contract.json``. A template's
  Outputs may be a subset of its contract entry while the R3 skeleton
  placeholder is in place, and must equal it once its ticket has removed the
  placeholder;
- every parameter value comes from evidence or a decision record, never from
  memory (handoff §7a): the account id and admin role from R1 evidence, the
  model list from the OD7 record, the zone and S3 prefix list from R3
  evidence once that evidence exists.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from tools import aws_template_guard as guard
from tools.evidence_secret_scan import _normalised_bytes

AWS_DIR = Path("deploy") / "aws"
CONTRACT_PATH = AWS_DIR / "outputs_contract.json"
EVIDENCE_V2 = Path("docs") / "infrastructure_security" / "evidence_v2"
DECISION_LOG = Path("docs") / "tier4_orchestration_state" / "decision_log"
OD1_RECORD = DECISION_LOG / "aws-redeployment-od1-region-r1_2026-10-21.json"
OD7_RECORD = DECISION_LOG / "aws-redeployment-od7-model-set_2026-10-21.json"
OD6_RECORD = DECISION_LOG / "aws-redeployment-od6-stack-layout-r3_2026-10-22.json"

PLACEHOLDER = "SkeletonPlaceholder"
STACK_ORDER = ["network", "iam", "kms", "audit", "secret", "host"]
COMMON_PARAMETERS = {"ProjectName", "ExpectedAccountId", "ExpectedRegion"}


def _json(path: Path) -> Any:
    return json.loads(_normalised_bytes(path).decode("utf-8-sig"))


def _text(path: Path) -> str:
    return _normalised_bytes(path).decode("utf-8-sig", errors="replace")


CONTRACT = _json(CONTRACT_PATH)
STACKS = {stack["key"]: stack for stack in CONTRACT["stacks"]}


def _template(key: str) -> dict[str, Any]:
    return guard.load_template(Path(STACKS[key]["template"]))


def _parameters(key: str) -> dict[str, str]:
    entries = _json(Path(STACKS[key]["parameters"]))
    assert all(set(e) == {"ParameterKey", "ParameterValue"} for e in entries)
    keys = [e["ParameterKey"] for e in entries]
    assert len(keys) == len(set(keys)), f"duplicate parameter in {key}"
    return {e["ParameterKey"]: e["ParameterValue"] for e in entries}


def _od7_resources() -> dict[str, list[str]]:
    record = _json(OD7_RECORD)
    (entry,) = [d for d in record["decisions"] if d["id"] == "OD7-resources"]
    return entry["answer"]


# --- layout -------------------------------------------------------------------


def test_stacks_are_the_six_in_deploy_order() -> None:
    assert [s["key"] for s in sorted(CONTRACT["stacks"], key=lambda s: s["order"])] == STACK_ORDER
    assert [s["order"] for s in CONTRACT["stacks"]] == list(range(1, 7))


@pytest.mark.parametrize("key", STACK_ORDER)
def test_stack_names_and_lifecycle(key: str) -> None:
    stack = STACKS[key]
    is_host = key == "host"

    assert stack["stack_name"] == f"{CONTRACT['project']}-{key}"
    assert stack["lifecycle"] == ("per_session" if is_host else "base")
    assert stack["hourly_cost"] is is_host
    assert stack["exports"] is (not is_host)
    assert Path(stack["template"]).is_file()
    assert Path(stack["parameters"]).is_file()
    assert Path(stack["template"]).stat().st_size <= guard.TEMPLATE_BODY_LIMIT


def test_every_template_file_is_in_the_contract() -> None:
    on_disk = {p.as_posix() for p in (AWS_DIR / "templates").iterdir()}
    assert on_disk == {s["template"] for s in CONTRACT["stacks"]}


@pytest.mark.parametrize("key", STACK_ORDER)
def test_template_metadata_names_its_stack(key: str) -> None:
    meta = _template(key)["Metadata"]["ProposalOrchestrator"]

    assert meta["Stack"] == key
    assert meta["StackName"] == STACKS[key]["stack_name"]
    assert meta["FilledBy"] == STACKS[key]["ticket"]
    assert meta["Contract"] == CONTRACT_PATH.as_posix()
    assert meta["Decision"] == CONTRACT["decision"] == OD6_RECORD.stem


# --- target guard ---------------------------------------------------------------


@pytest.mark.parametrize("key", STACK_ORDER)
def test_template_guards_its_account_and_region(key: str) -> None:
    template = _template(key)
    params = template["Parameters"]

    assert COMMON_PARAMETERS <= set(params)
    assert params["ProjectName"]["AllowedValues"] == [CONTRACT["project"]]
    assert "Default" not in params["ExpectedAccountId"]
    assert params["ExpectedRegion"]["Default"] == "eu-north-1"
    assertions = [a["Assert"] for a in template["Rules"]["DeployTarget"]["Assertions"]]
    assert {"Fn::Equals": [{"Ref": "ExpectedAccountId"}, {"Ref": "AWS::AccountId"}]} in assertions
    assert {"Fn::Equals": [{"Ref": "ExpectedRegion"}, {"Ref": "AWS::Region"}]} in assertions


# --- outputs contract -----------------------------------------------------------


def test_contract_export_names_follow_the_rule() -> None:
    seen: set[str] = set()
    for stack in CONTRACT["stacks"]:
        for key, output in stack["outputs"].items():
            assert re.fullmatch(r"[A-Z][A-Za-z0-9]+", key)
            assert output["consumers"], f"{stack['key']}.{key} has no consumer"
            if stack["exports"]:
                assert output["export"] == f"{CONTRACT['project']}-{stack['key']}-{key}"
                assert output["export"] not in seen
                seen.add(output["export"])
            else:
                assert output["export"] is None


def test_contract_names_what_the_handoff_asks_for() -> None:
    """R3 handoff §3: every id later tickets and R12a need."""
    named = {(s["key"], k) for s in CONTRACT["stacks"] for k in s["outputs"]}
    required = {
        ("network", "VpcId"), ("network", "PrivateSubnetId"), ("network", "PrivateRouteTableId"),
        ("network", "HostSecurityGroupId"), ("network", "EndpointSecurityGroupId"),
        ("network", "S3GatewayEndpointId"),
        ("iam", "RuntimeRoleName"), ("iam", "RuntimeRoleArn"),
        ("iam", "InstanceProfileName"), ("iam", "InstanceProfileArn"),
        ("kms", "KeyArn"), ("kms", "KeyAliasName"),
        ("audit", "TrailBucketName"), ("audit", "DeployBucketName"), ("audit", "TrailArn"),
        ("audit", "FlowLogGroupName"),
        ("secret", "SecretArn"),
        ("host", "BedrockRuntimeEndpointId"), ("host", "StsEndpointId"),
        ("host", "SecretsManagerEndpointId"), ("host", "SsmEndpointId"),
        ("host", "SsmMessagesEndpointId"), ("host", "Ec2MessagesEndpointId"), ("host", "InstanceId"),
    }  # fmt: skip
    assert required <= named


@pytest.mark.parametrize("key", STACK_ORDER)
def test_template_outputs_match_the_contract(key: str) -> None:
    template = _template(key)
    outputs = template.get("Outputs") or {}
    contract = STACKS[key]["outputs"]

    if PLACEHOLDER in (template.get("Resources") or {}):
        assert set(outputs) <= set(contract), "skeleton outputs outside the contract"
    else:
        assert set(outputs) == set(contract), "filled template must name exactly the contract outputs"
    for name, output in outputs.items():
        export = (output.get("Export") or {}).get("Name")
        assert export == contract[name]["export"], name


@pytest.mark.parametrize("key", STACK_ORDER)
def test_placeholder_does_not_outlive_its_ticket(key: str) -> None:
    resources = _template(key)["Resources"]
    if PLACEHOLDER in resources:
        assert len(resources) == 1, "remove the skeleton placeholder when the stack is filled"
        assert resources[PLACEHOLDER]["Type"] == "AWS::CloudFormation::WaitConditionHandle"


# --- parameter files -------------------------------------------------------------


@pytest.mark.parametrize("key", STACK_ORDER)
def test_parameter_file_matches_its_template(key: str) -> None:
    declared = _template(key)["Parameters"]
    values = _parameters(key)
    from_evidence = STACKS[key]["parameters_from_evidence"]

    assert set(values) <= set(declared), "value for an undeclared parameter"
    for name, spec in declared.items():
        if "Default" in spec:
            continue
        if name in from_evidence and not Path(from_evidence[name]).exists():
            assert name not in values, f"{name} set before its evidence {from_evidence[name]} exists"
        else:
            assert name in values, f"no value for required parameter {name}"
        if name in values and "AllowedPattern" in spec:
            assert re.fullmatch(spec["AllowedPattern"], values[name]), name


@pytest.mark.parametrize("key", STACK_ORDER)
def test_parameters_from_evidence_appear_in_that_evidence(key: str) -> None:
    values = _parameters(key)
    for name, evidence in STACKS[key]["parameters_from_evidence"].items():
        assert evidence.startswith(EVIDENCE_V2.as_posix() + "/R3/")
        if name in values:
            assert values[name] in _text(Path(evidence)), f"{name} is not in {evidence}"


@pytest.mark.parametrize("key", STACK_ORDER)
def test_account_and_region_values_come_from_records(key: str) -> None:
    values = _parameters(key)
    caller = _json(EVIDENCE_V2 / "R1" / "R1_00_caller-identity.json")
    od1 = _json(OD1_RECORD)
    (od1_answer,) = [d["answer"] for d in od1["decisions"] if d["id"] == "OD1-r1"]

    assert values["ExpectedAccountId"] == caller["Account"]
    assert values.get("ExpectedRegion", "eu-north-1") == "eu-north-1"
    assert od1_answer.startswith("eu-north-1")


# R6-D4: the kms stack takes no AdminRoleArn (root delegates to IAM); only the
# secret stack (R8) still names the admin role.
@pytest.mark.parametrize("key", ["secret"])
def test_admin_role_is_the_r1_role_arn_with_its_path(key: str) -> None:
    role = _json(EVIDENCE_V2 / "R1" / "R1_00_role.json")["Role"]

    assert _parameters(key)["AdminRoleArn"] == role["Arn"]
    assert role["Path"] in role["Arn"]


@pytest.mark.parametrize("key", ["iam", "host"])
def test_model_lists_equal_the_od7_record(key: str) -> None:
    values = _parameters(key)
    od7 = _od7_resources()

    assert values["InferenceProfileArns"].split(",") == od7["inference_profiles"]
    assert values["FoundationModelArns"].split(",") == od7["foundation_models"]
    assert not any(":inference-profile/global." in arn for arn in od7["inference_profiles"])


def test_routed_regions_are_the_regions_of_the_od7_models() -> None:
    regions = []
    for arn in _od7_resources()["foundation_models"]:
        region = arn.split(":")[3]
        if region not in regions:
            regions.append(region)

    assert _parameters("iam")["RoutedRegions"].split(",") == regions


def test_transport_model_is_the_od7_orchestrator_profile() -> None:
    model = _parameters("secret")["TransportModelId"]
    record = _json(OD7_RECORD)
    (answer,) = [d["answer"] for d in record["decisions"] if d["id"] == "OD7-orchestrator"]

    assert answer.startswith(model + ",")
    assert any(arn.endswith("/" + model) for arn in _od7_resources()["inference_profiles"])


# --- decision record -------------------------------------------------------------


def test_od6_successor_record_supersedes_od6_only() -> None:
    record = _json(OD6_RECORD)

    assert record["id"] == OD6_RECORD.stem
    assert record["supersedes"].startswith("aws-redeployment-operator-decisions_2026-10-21, decision OD6 only")
    assert record["review_state"] == "operator_decided"
