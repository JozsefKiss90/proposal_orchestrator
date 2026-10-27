"""R8 — the filled runtime secret template (``deploy/aws/templates/50-secret.yaml``).

Acceptance, from ``plans/aws_redeployment_tickets.md`` R8, the R8 handoff
(``plans/aws_redeployment_r8_handoff_2026-10-26.md`` §3, §4) and the
operator's answers of 2026-10-26 (decision record
``aws-redeployment-r8-secret_2026-10-26``, R8-D1 to R8-D16):

- exactly one secret and one resource policy; the secret is
  ``${ProjectName}/env-config``, retained on deletion and replacement (R8-D5),
  encrypted with the imported ``KeyArn`` (R8-D16, DC-20), with no rotation
  and no replica (R8-D6);
- its value is one JSON object of exactly the five agreed keys, the preset
  ``BEDROCK_CONVERSE_EU`` (R8-D3), production mode ``true``, diagnostic level
  ``metadata``, the Region from ``AWS::Region`` and the model from
  ``TransportModelId`` (R8-D2); no credential-shaped key;
- the resource policy is deny-only with ``BlockPublicPolicy`` (R8-D4) and
  exactly the four agreed statements (R8-D12, R8-D13, DC-21); no statement
  touches the policy-management actions or ``DescribeSecret`` for any
  principal but the runtime role, and the admin exception matches the role
  with and without its path;
- imports are exactly the exports whose consumers name R8; outputs are the
  contract; only the project tag (R8-D15).

The name of the value property is one of the four patterns of
``tools/evidence_secret_scan.py``; it is assembled here, as in
``tools/env_config_digest.py``, so that no test id or failure line in an
evidence file can carry it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools import aws_template_guard as guard
from tools import env_config_digest

TEMPLATE = Path("deploy") / "aws" / "templates" / "50-secret.yaml"
PARAMETERS = Path("deploy") / "aws" / "parameters" / "secret.json"
CONTRACT = Path("deploy") / "aws" / "outputs_contract.json"
CONFIG = Path("runner") / "transport" / "config.py"
RECORD = Path("docs/tier4_orchestration_state/decision_log/aws-redeployment-r8-secret_2026-10-26.json")
R1_ROLE = Path("docs/infrastructure_security/evidence_v2/R1/R1_00_role.json")
R8_ADMIN_ROLE = Path("docs/infrastructure_security/evidence_v2/R8/R8_03_admin-role.json")

VALUE_FIELD = env_config_digest.VALUE_FIELD

RUNTIME_ROLE = {"Fn::ImportValue": "proposal-orchestrator-iam-RuntimeRoleArn"}
ADMIN_WITH_PATH = {"Ref": "AdminRoleArn"}
ADMIN_WITHOUT_PATH = {
    "Fn::Sub": [
        "arn:${AWS::Partition}:iam::${AWS::AccountId}:role/${AdminRoleName}",
        {"AdminRoleName": {"Fn::Select": [2, {"Fn::Split": ["/", {"Ref": "AdminRoleArn"}]}]}},
    ]
}

CHANGE_ACTIONS = [
    "secretsmanager:PutSecretValue",
    "secretsmanager:UpdateSecret",
    "secretsmanager:UpdateSecretVersionStage",
    "secretsmanager:DeleteSecret",
    "secretsmanager:RestoreSecret",
    "secretsmanager:RotateSecret",
    "secretsmanager:CancelRotateSecret",
    "secretsmanager:TagResource",
    "secretsmanager:UntagResource",
    "secretsmanager:ReplicateSecretToRegions",
    "secretsmanager:RemoveRegionsFromReplication",
    "secretsmanager:StopReplicationToReplica",
]
# R8-D12: never denied to a principal of the account other than the runtime role.
LOCKOUT_SAFE_ACTIONS = {
    "secretsmanager:GetResourcePolicy",
    "secretsmanager:PutResourcePolicy",
    "secretsmanager:DeleteResourcePolicy",
    "secretsmanager:DescribeSecret",
}

EXPECTED_POLICY: dict[str, dict[str, Any]] = {
    "DenyRuntimeRoleExceptGetSecretValue": {
        "Effect": "Deny",
        "Principal": "*",
        "NotAction": "secretsmanager:GetSecretValue",
        "Resource": "*",
        "Condition": {"ArnEquals": {"aws:PrincipalArn": RUNTIME_ROLE}},
    },
    "DenyValueReadExceptRuntimeAndAdmin": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "secretsmanager:GetSecretValue",
        "Resource": "*",
        "Condition": {"ArnNotLike": {"aws:PrincipalArn": [RUNTIME_ROLE, ADMIN_WITH_PATH, ADMIN_WITHOUT_PATH]}},
    },
    "DenyChangesExceptAdmin": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": CHANGE_ACTIONS,
        "Resource": "*",
        "Condition": {"ArnNotLike": {"aws:PrincipalArn": [ADMIN_WITH_PATH, ADMIN_WITHOUT_PATH]}},
    },
    "DenyPrincipalsOutsideAccount": {
        "Effect": "Deny",
        "Principal": "*",
        "Action": "secretsmanager:*",
        "Resource": "*",
        "Condition": {"StringNotEquals": {"aws:PrincipalAccount": {"Ref": "AWS::AccountId"}}},
    },
}


def _template() -> dict[str, Any]:
    return guard.load_template(TEMPLATE)


def _resources() -> dict[str, Any]:
    return _template()["Resources"]


def _props(name: str) -> dict[str, Any]:
    return _resources()[name]["Properties"]


def _parameters() -> dict[str, str]:
    return {p["ParameterKey"]: p["ParameterValue"] for p in json.loads(PARAMETERS.read_text(encoding="utf-8-sig"))}


def _by_sid() -> dict[str, dict[str, Any]]:
    document = _props("EnvConfigSecretPolicy")["ResourcePolicy"]
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


def _actions(statement: dict[str, Any]) -> set[str]:
    action = statement.get("Action", [])
    return set([action] if isinstance(action, str) else action)


def test_exactly_the_secret_and_its_policy() -> None:
    assert {name: r["Type"] for name, r in _resources().items()} == {
        "EnvConfigSecret": "AWS::SecretsManager::Secret",
        "EnvConfigSecretPolicy": "AWS::SecretsManager::ResourcePolicy",
    }


def test_secret_is_retained_and_its_policy_is_not() -> None:
    secret = _resources()["EnvConfigSecret"]
    policy = _resources()["EnvConfigSecretPolicy"]

    assert secret["DeletionPolicy"] == "Retain"
    assert secret["UpdateReplacePolicy"] == "Retain"
    assert "DeletionPolicy" not in policy
    assert "UpdateReplacePolicy" not in policy


def test_secret_name_is_the_r5_grant_name() -> None:
    assert _props("EnvConfigSecret")["Name"] == {"Fn::Sub": "${ProjectName}/env-config"}
    iam = Path("deploy/aws/templates/20-iam.yaml").read_text(encoding="utf-8")
    assert ":secret:${ProjectName}/env-config-*" in iam


def test_secret_uses_the_imported_key_arn() -> None:
    assert _props("EnvConfigSecret")["KmsKeyId"] == {"Fn::ImportValue": "proposal-orchestrator-kms-KeyArn"}


def test_no_rotation_no_replica_no_generated_value() -> None:
    props = _props("EnvConfigSecret")

    assert set(props) == {"Name", "Description", "KmsKeyId", VALUE_FIELD, "Tags"}
    assert not any(r["Type"] == "AWS::SecretsManager::RotationSchedule" for r in _resources().values())


def test_value_is_the_five_agreed_keys_from_parameters_and_region() -> None:
    value = _props("EnvConfigSecret")[VALUE_FIELD]
    obj = env_config_digest.expected_object(TEMPLATE, PARAMETERS, "eu-north-1")

    assert set(value) == {"Fn::Sub"}
    assert "${AWS::Region}" in value["Fn::Sub"]
    assert "${TransportModelId}" in value["Fn::Sub"]
    assert obj == {
        "ORCHESTRATOR_TRANSPORT_PRESET": "BEDROCK_CONVERSE_EU",
        "ORCHESTRATOR_PRODUCTION_MODE": "true",
        "ORCHESTRATOR_DIAGNOSTIC_LEVEL": "metadata",
        "AWS_REGION": "eu-north-1",
        "ORCHESTRATOR_TRANSPORT_MODEL": _parameters()["TransportModelId"],
    }


def test_value_holds_no_credential_shaped_key() -> None:
    obj = env_config_digest.expected_object(TEMPLATE, PARAMETERS, "eu-north-1")
    for key in obj:
        assert not any(word in key.upper() for word in ("KEY", "SECRET", "TOKEN", "PASSWORD")), key


def test_preset_name_is_the_lasting_r9e_rule() -> None:
    # R8-D3: the name is fixed here; R9e adds it to runner/transport/config.py.
    # Until then the launcher fails closed on the unknown preset. Once R9e
    # lands, its own test asserts the preset exists.
    obj = env_config_digest.expected_object(TEMPLATE, PARAMETERS, "eu-north-1")
    assert obj["ORCHESTRATOR_TRANSPORT_PRESET"] == "BEDROCK_CONVERSE_EU"
    assert "BEDROCK_CONVERSE_US" in CONFIG.read_text(encoding="utf-8")


def test_digest_is_canonical_and_order_independent() -> None:
    obj = env_config_digest.expected_object(TEMPLATE, PARAMETERS, "eu-north-1")
    reordered = dict(reversed(list(obj.items())))

    assert env_config_digest.digest(obj) == env_config_digest.digest(reordered)
    assert env_config_digest.canonical_json(obj).startswith(b'{"AWS_REGION":')


def test_resource_policy_is_deny_only_with_block_public_policy() -> None:
    props = _props("EnvConfigSecretPolicy")

    assert props["SecretId"] == {"Ref": "EnvConfigSecret"}
    assert props["BlockPublicPolicy"] is True
    assert all(s["Effect"] == "Deny" for s in _by_sid().values())


def test_resource_policy_is_exactly_the_decided_denies() -> None:
    assert _by_sid() == EXPECTED_POLICY


def test_no_deny_touches_lockout_safe_actions_except_for_the_runtime_role() -> None:
    for sid, statement in _by_sid().items():
        if sid == "DenyRuntimeRoleExceptGetSecretValue":
            assert statement["Condition"] == {"ArnEquals": {"aws:PrincipalArn": RUNTIME_ROLE}}
            continue
        if sid == "DenyPrincipalsOutsideAccount":
            assert set(statement["Condition"]) == {"StringNotEquals"}
            continue
        assert not _actions(statement) & LOCKOUT_SAFE_ACTIONS, sid
        assert "secretsmanager:*" not in _actions(statement), sid


def test_change_actions_are_api_operations() -> None:
    operations = {
        "BatchGetSecretValue", "CancelRotateSecret", "CreateSecret", "DeleteResourcePolicy", "DeleteSecret",
        "DescribeSecret", "GetRandomPassword", "GetResourcePolicy", "GetSecretValue", "ListSecrets",
        "ListSecretVersionIds", "PutResourcePolicy", "PutSecretValue", "RemoveRegionsFromReplication",
        "ReplicateSecretToRegions", "RestoreSecret", "RotateSecret", "StopReplicationToReplica",
        "TagResource", "UntagResource", "UpdateSecret", "UpdateSecretVersionStage", "ValidateResourcePolicy",
    }
    assert {a.split(":", 1)[1] for a in CHANGE_ACTIONS} <= operations


def test_admin_without_path_form_resolves_to_the_role_name() -> None:
    arn = _parameters()["AdminRoleArn"]
    parts = arn.split("/")

    assert len(parts) == 3, "AdminRoleArn must carry exactly one path segment for Fn::Select [2]"
    assert parts[1] == "managed"
    assert parts[2] == "AccountFullAccessRole"
    for evidence in (R1_ROLE, R8_ADMIN_ROLE):
        if evidence.exists():
            text = evidence.read_text(encoding="utf-8-sig")
            assert arn in text, evidence


def test_imports_are_exactly_the_exports_that_name_r8_as_consumer() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
    wanted = {
        output["export"]
        for stack in contract["stacks"]
        for output in stack["outputs"].values()
        if "R8" in output["consumers"]
    }

    assert set(_imports(_resources())) == wanted
    assert wanted == {"proposal-orchestrator-iam-RuntimeRoleArn", "proposal-orchestrator-kms-KeyArn"}


def test_no_literal_role_or_key_arn() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "runtime-role" not in text
    assert "AccountFullAccessRole" not in text
    assert ":key/" not in text


def test_only_the_project_tag() -> None:
    for name, resource in _resources().items():
        if resource["Type"] in guard.UNTAGGABLE_TYPES:
            continue
        assert resource["Properties"]["Tags"] == [{"Key": "project", "Value": {"Ref": "ProjectName"}}], name


def test_outputs_are_the_contract_with_their_values() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
    (secret,) = [s for s in contract["stacks"] if s["key"] == "secret"]
    outputs = _template()["Outputs"]

    assert {k: v["Export"]["Name"] for k, v in outputs.items()} == {
        k: v["export"] for k, v in secret["outputs"].items()
    }
    assert outputs["SecretArn"]["Value"] == {"Ref": "EnvConfigSecret"}
    assert outputs["SecretName"]["Value"] == {"Fn::Sub": "${ProjectName}/env-config"}


def test_metadata_names_the_fill_decision() -> None:
    meta = _template()["Metadata"]["ProposalOrchestrator"]

    assert meta["Decision"] == "aws-redeployment-od6-stack-layout-r3_2026-10-22"
    assert meta["FillDecision"] == "aws-redeployment-r8-secret_2026-10-26"
    assert RECORD.exists()
