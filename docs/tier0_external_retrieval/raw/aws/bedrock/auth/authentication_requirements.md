---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-authentication-requirements"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/inference-prereq.md"
source_title: "Authentication requirements for Amazon Bedrock"
retrieval_query: "IAM permissions policy bedrock runtime actions service role access control bedrock:InvokeModel bedrock:Converse identity-based policy"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "authentication_requirements"
components:
  - "IAM"
  - "boto3"
  - "credentials"
  - "bedrock:CallWithBearerToken"
notes:
  - "Authentication is IAM-based; covered in conjunction with IAM requirements"
  - "Coverage is partial — no dedicated authentication configuration doc was retrieved"
---

# Authentication Requirements

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/inference-prereq.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-modify.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-runtime_example_bedrock-runtime_InvokeModel_AnthropicClaude_section.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "IAM permissions policy bedrock runtime actions service role access control bedrock:InvokeModel bedrock:Converse identity-based policy"

## Retrieved Documentation

### IAM-Based Authentication

All Amazon Bedrock API access is authenticated via AWS IAM. The boto3 client resolves credentials from the standard AWS credential chain.

### Client Initialization

```python
import boto3

# Credentials resolved from standard AWS credential chain:
# 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
# 2. Shared credentials file (~/.aws/credentials)
# 3. AWS config file (~/.aws/config)
# 4. Instance metadata (EC2 instance role)
# 5. Container credentials (ECS task role)
client = boto3.client("bedrock-runtime", region_name="us-east-1")
```

### Required IAM Actions for Inference

- `bedrock:InvokeModel` — Required for both `InvokeModel` and `Converse` API calls.
- `bedrock:InvokeModelWithResponseStream` — Required for streaming invocations.

### API Key Authentication (Bearer Token)

An alternative authentication method uses API keys with the `bedrock:CallWithBearerToken` action:

```json
{
    "Effect": "Allow",
    "Action": [
        "bedrock:CallWithBearerToken"
    ],
    "Resource": "*"
}
```

### Regional Client Configuration

The `region_name` parameter determines which regional endpoint the client connects to:

```python
# US East 1
client = boto3.client("bedrock-runtime", region_name="us-east-1")

# US West 2
client = boto3.client("bedrock-runtime", region_name="us-west-2")
```

## Integration Relevance

- **Backend transport:** The transport layer must ensure valid AWS credentials are available before making Bedrock API calls. The boto3 client handles credential resolution automatically.
- **Authentication:** IAM-based. The calling identity (user, role, or service) must have `bedrock:InvokeModel` permission. For streaming, `bedrock:InvokeModelWithResponseStream` is also required.
- **Request construction:** No authentication-specific headers are needed when using the AWS SDK — the SDK signs requests automatically with SigV4.
- **Response parsing:** No authentication-specific response parsing.
- **Error handling:** `AccessDeniedException` indicates missing IAM permissions. `UnauthorizedException` may indicate credential issues.
- **Streaming:** Requires additional IAM action `bedrock:InvokeModelWithResponseStream`.
- **Tool use:** No additional authentication requirements for tool use.
