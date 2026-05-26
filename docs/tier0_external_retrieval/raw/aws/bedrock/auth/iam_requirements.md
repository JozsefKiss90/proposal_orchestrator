---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-iam-requirements"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/inference-prereq.md"
source_title: "Amazon Bedrock IAM policies / IAM prerequisites for inference"
retrieval_query: "IAM permissions policy bedrock runtime actions service role access control bedrock:InvokeModel bedrock:Converse identity-based policy"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "iam_requirements"
components:
  - "IAM"
  - "bedrock:InvokeModel"
  - "bedrock:InvokeModelWithResponseStream"
  - "bedrock:Converse"
notes:
  - "bedrock:InvokeModel covers both InvokeModel and Converse operations"
---

# AWS IAM Requirements for Bedrock

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/inference-prereq.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/prov-thru-prereq.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-modify.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/rag-eval-service-roles.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "IAM permissions policy bedrock runtime actions service role access control bedrock:InvokeModel bedrock:Converse identity-based policy"

## Retrieved Documentation

### Key IAM Actions

- `bedrock:InvokeModel` — Required to carry out model invocation. Allows the role to call the `InvokeModel` and `Converse` API operations.
- `bedrock:InvokeModelWithResponseStream` — Required for streaming invocation.
- `bedrock:CallWithBearerToken` — Required for API key-based access.

### Resource ARN Formats

Foundation model ARN:
```
arn:aws:bedrock:{region}::foundation-model/{model-id}
```

Inference profile ARN:
```
arn:aws:bedrock:{region}:{account-id}:inference-profile/{profile-id}
```

Provisioned model ARN:
```
arn:aws:bedrock:{region}:{account-id}:provisioned-model/{model-id}
```

### Minimal IAM Policy for Model Invocation

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "arn:aws:bedrock:{region}::foundation-model/*"
        }
    ]
}
```

### Comprehensive IAM Policy (Provisioned Throughput)

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PermissionsForProvisionedThroughput",
            "Effect": "Allow",
            "Action": [
                "bedrock:GetFoundationModel",
                "bedrock:ListFoundationModels",
                "bedrock:GetCustomModel",
                "bedrock:ListCustomModels",
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListTagsForResource",
                "bedrock:UntagResource",
                "bedrock:TagResource",
                "bedrock:CreateProvisionedModelThroughput",
                "bedrock:GetProvisionedModelThroughput",
                "bedrock:ListProvisionedModelThroughputs",
                "bedrock:UpdateProvisionedModelThroughput",
                "bedrock:DeleteProvisionedModelThroughput"
            ],
            "Resource": "*"
        }
    ]
}
```

### Scoped Policy with Inference Profile Condition

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel*"
            ],
            "Resource": [
                "arn:aws:bedrock:us-west-2:111122223333:inference-profile/us.anthropic.claude-3-haiku-20240307-v1:0"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel*"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
                "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
            ],
            "Condition": {
                "StringLike": {
                    "bedrock:InferenceProfileArn": "arn:aws:bedrock:us-west-2:111122223333:inference-profile/us.anthropic.claude-3-haiku-20240307-v1:0"
                }
            }
        }
    ]
}
```

## Integration Relevance

- **Backend transport:** The IAM role attached to the runtime environment must have `bedrock:InvokeModel` permission at minimum. This single action covers both InvokeModel and Converse API calls.
- **Authentication:** All Bedrock access is IAM-based. The boto3 client resolves credentials from the standard AWS credential chain (environment variables, shared credentials file, instance role, etc.).
- **Request construction:** No IAM-specific request construction required beyond standard AWS SDK credential resolution.
- **Response parsing:** No IAM-specific response parsing.
- **Error handling:** Missing IAM permissions result in `AccessDeniedException` from the AWS API.
- **Streaming:** Streaming invocation requires `bedrock:InvokeModelWithResponseStream` in addition to `bedrock:InvokeModel`.
- **Tool use:** No additional IAM actions required for tool use; it is handled within the Converse API call.
