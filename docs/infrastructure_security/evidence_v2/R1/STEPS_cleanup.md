# R1 — Part C: cleanup of the Explore AWS leftovers

| Field | Value |
|---|---|
| Written from | `R1_22_inventory-before.json`, `R1_00_roles.json`, `R1_31_cleanup-inspection.json` |
| Written by / on | agent (Claude) / 2026-10-21 |
| Account / region | `797661577394` / `eu-north-1` (IAM is global) |

Every item below was created on 2026-10-19 by the Explore AWS exercises and is used by nothing the
redeployment needs. Deleting is irreversible. Nothing else is touched: the default VPC, the roles
under `/managed/` and `/aws-service-role/` (including `AWSServiceRoleForRDS`), and the 10 USD budget
stay.

**Do C1 first.** `lambda_test` has a public Function URL and runs as `PowerUserRole`
(`PowerUserAccess`), so it is an open entry into the account until it is gone.

Run in CloudShell (us-east-1 session), in `~/R1`. Each block appends its output to the cleanup log.

### C1 — Lambda: Function URL, function, log group

```bash
cd ~/R1; R=eu-north-1
{ echo "== C1 $(date -u +%FT%TZ)"
  aws lambda delete-function-url-config --region $R --function-name lambda_test && echo "url deleted"
  aws lambda delete-function --region $R --function-name lambda_test && echo "function deleted"
  aws logs delete-log-group --region $R --log-group-name /aws/lambda/lambda_test && echo "log group deleted"
} 2>&1 | tee -a R1_33_cleanup-log.txt
```

### C2 — EC2: security group and key pair

```bash
cd ~/R1; R=eu-north-1
{ echo "== C2 $(date -u +%FT%TZ)"
  aws ec2 delete-security-group --region $R --group-id sg-085c137a9e87fc7ba && echo "sg launch-wizard-1 deleted"
  aws ec2 delete-key-pair --region $R --key-pair-id key-07c12e181fa44fed9 --output json && echo "key pair test-key deleted"
} 2>&1 | tee -a R1_33_cleanup-log.txt
```

If you downloaded `test-key.pem` on the workstation, delete that file yourself as well.

### C3 — IAM: the three Explore roles

```bash
cd ~/R1
{ echo "== C3 $(date -u +%FT%TZ)"
  aws iam detach-role-policy --role-name PowerUserRole --policy-arn arn:aws:iam::aws:policy/PowerUserAccess && \
  aws iam delete-role --role-name PowerUserRole && echo "PowerUserRole deleted"
  aws iam detach-role-policy --role-name PowerUser-lambda-1 --policy-arn arn:aws:iam::aws:policy/PowerUserAccess && \
  aws iam delete-role --role-name PowerUser-lambda-1 && echo "PowerUser-lambda-1 deleted"
  aws iam detach-role-policy --role-name rds-monitoring-role --policy-arn arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole && \
  aws iam delete-role --role-name rds-monitoring-role && echo "rds-monitoring-role deleted"
} 2>&1 | tee -a R1_33_cleanup-log.txt
```

| Evidence file | PASS criterion |
|---|---|
| `R1_33_cleanup-log.txt` | Every line after a command reads "… deleted"; no error |

### C4 — Inventory after cleanup

```bash
cd ~/R1
bash r1_inventory.sh R1_34_inventory-after.json
aws iam list-roles --query 'Roles[].{name:RoleName,path:Path}' --output json > R1_35_roles-after.json
aws logs describe-log-groups --region eu-north-1 --query 'logGroups[].logGroupName' --output json > R1_36_log-groups-after.json
jq '{regions_with_findings, regions_with_errors}' R1_34_inventory-after.json; jq -r '.[] | select(.path=="/") | .name' R1_35_roles-after.json; cat R1_36_log-groups-after.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_34_inventory-after.json` | `regions_with_findings` is empty; `regions_with_errors` holds only the 16 Regions denied in `R1_26` |
| `R1_35_roles-after.json` | No role with path `/` remains (only `/managed/` and `/aws-service-role/` roles) |
| `R1_36_log-groups-after.json` | Empty list |
