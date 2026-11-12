# AWS cost check, 2026-11-12T11:46:01Z

Account `797661577394`, Region `eu-north-1`.

## Credits and budget

- Plan FREE ACTIVE, credits remaining 199.19 USD, expires 2027-04-19T09:00:47.635000+00:00.
- Budget `My Monthly Cost Budget`: limit 10.0 USD, spend 0.523 USD.
- Approved amount: pending HUF (pending: the ELTE IK financial office has not approved the reimbursement route (plans/aws_redeployment_handoff_2026-10-21.md, Funding). The figure of about 300,000 HUF is not an approved amount.).

## Month to date (2026-11-01 to 2026-11-12)

- Usage: 0.522633 USD.
  - AWS CloudFormation: 0.0
  - AWS CloudTrail: 0.0
  - AWS Glue: 0.0
  - AWS Key Management Service: 0.359722
  - AWS Secrets Manager: 0.145015
  - Amazon Simple Storage Service: 0.017625
  - Amazon Virtual Private Cloud: 2e-06
  - AmazonCloudWatch: 0.0
  - Claude Opus 4.6 (Amazon Bedrock Edition): 0.000269
- Credit: -0.522634 USD.
  - AWS Key Management Service: -0.359723
  - AWS Secrets Manager: -0.145015
  - Amazon Simple Storage Service: -0.017625
  - Amazon Virtual Private Cloud: -2e-06
  - Claude Opus 4.6 (Amazon Bedrock Edition): -0.000269

## Host stack per hour

- Running: 0.154686 USD (host 0.09077, endpoints 0.063, root volume 0.000916).
- Stopped: 0.063916 USD (endpoints and root volume).

## Host creations since 2026-08-14T11:46:01Z

| Change set | Start | End | Hours | Stack cost (upper), USD | Tokens in / out per model | Token cost, USD |
|---|---|---|---|---|---|---|
| `r11-create-01` | 2026-11-11T20:12:14Z | 2026-11-11T20:50:13Z | 0.633 | 0.0979 | eu.anthropic.claude-opus-4-6-v1: 0 / 0 | eu.anthropic.claude-opus-4-6-v1: 0.0 |
| `r11-fix1-create-01` | 2026-11-11T21:03:42Z | 2026-11-11T21:09:27Z | 0.096 | 0.0148 | eu.anthropic.claude-opus-4-6-v1: 14 / 7 | eu.anthropic.claude-opus-4-6-v1: 0.000269 |
| `r11-create-02` | 2026-11-11T21:51:19Z | 2026-11-11T21:55:18Z | 0.066 | 0.0102 | eu.anthropic.claude-opus-4-6-v1: 0 / 0 | eu.anthropic.claude-opus-4-6-v1: 0.0 |
| `r12b-create-01` | 2026-11-11T23:36:41Z | 2026-11-11T23:41:22Z | 0.078 | 0.0121 | eu.anthropic.claude-opus-4-6-v1: 0 / 0 | eu.anthropic.claude-opus-4-6-v1: 0.0 |
| `r12b-create-02` | 2026-11-12T00:34:47Z | 2026-11-12T00:42:17Z | 0.125 | 0.0193 | eu.anthropic.claude-opus-4-6-v1: 14 / 7 | eu.anthropic.claude-opus-4-6-v1: 0.000269 |

## Prices

| Item | USD | Unit | Page | Read |
|---|---|---|---|---|
| host_hour | 0.09077 | Hrs | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20261110173852/eu-north-1/index.json | 2026-11-12 |
| gp3_gb_month | 0.0836 | GB-Mo | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20261110173852/eu-north-1/index.json | 2026-11-12 |
| endpoint_hour | 0.0105 | Hrs | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonVPC/20261105181945/eu-north-1/index.json | 2026-11-12 |
| endpoint_gb | 0.01 | GB | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonVPC/20261105181945/eu-north-1/index.json | 2026-11-12 |
| kms_key_month | 1.0 | Keys | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/awskms/20261108172342/eu-north-1/index.json | 2026-11-12 |
| kms_request | 3e-06 | Requests | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/awskms/20261108172342/eu-north-1/index.json | 2026-11-12 |
| secret_month | 0.4 | Secrets | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSSecretsManager/20261111195606/eu-north-1/index.json | 2026-11-12 |
| logs_ingest_gb | 0.54 | GB | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/20261104213532/eu-north-1/index.json | 2026-11-12 |
| logs_storage_gb_month | 0.028 | GB-Mo | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/20261104213532/eu-north-1/index.json | 2026-11-12 |
| eu.anthropic.claude-opus-4-6-v1 input | 5.5 | per 1000000 tokens | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrockFoundationModels/20261109224312/eu-north-1/index.json | 2026-11-12 |
| eu.anthropic.claude-opus-4-6-v1 output | 27.5 | per 1000000 tokens | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrockFoundationModels/20261109224312/eu-north-1/index.json | 2026-11-12 |
| eu.anthropic.claude-sonnet-4-6 input | 3.3 | per 1000000 tokens | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrockFoundationModels/20261109224312/eu-north-1/index.json | 2026-11-12 |
| eu.anthropic.claude-sonnet-4-6 output | 16.5 | per 1000000 tokens | https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrockFoundationModels/20261109224312/eu-north-1/index.json | 2026-11-12 |

## Notes

- stack_cost_usd_upper prices every hour of a creation as running; stopped hours cost less.
- Token counts come from the AWS/Bedrock CloudWatch metrics, summed over 5-minute periods that cover the creation.
- The monthly KMS key and secret charges are base costs, not per creation.
