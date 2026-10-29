# DC-14, DC-09: the host calls AWS as the runtime role through its instance profile, and IMDSv1 is refused.
# In: PO_REGION, PO_RUNTIME_ROLE_NAME, PO_INSTANCE_PROFILE_ARN.
echo "CHECK=dc14-caller-identity"
result=expected
arn=$(aws sts get-caller-identity --region "$PO_REGION" --query Arn --output text 2>/dev/null)
rc=$?
echo "sts_exit=$rc"
echo "caller_arn=$arn"
case "$arn" in
  *":assumed-role/$PO_RUNTIME_ROLE_NAME/"*) echo "caller_is_runtime_role=yes" ;;
  *) echo "caller_is_runtime_role=no"; result=unexpected ;;
esac
v1=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://169.254.169.254/latest/meta-data/ 2>/dev/null)
echo "imdsv1_http_status=$v1"
[ "$v1" = "401" ] || result=unexpected
token=$(curl -s -X PUT --max-time 3 -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' http://169.254.169.254/latest/api/token 2>/dev/null)
profile=$(curl -s --max-time 3 -H "X-aws-ec2-metadata-token: $token" http://169.254.169.254/latest/meta-data/iam/info 2>/dev/null \
  | python3 -c 'import json, sys; print(json.load(sys.stdin).get("InstanceProfileArn", ""))' 2>/dev/null)
token=""
echo "instance_profile_arn=$profile"
[ "$profile" = "$PO_INSTANCE_PROFILE_ARN" ] || result=unexpected
echo "RESULT=$result"
exit 0
