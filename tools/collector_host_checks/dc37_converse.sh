# DC-37 (DC-36 on the host): one Converse call through PrivateLink returns the fixed test string,
# as the runtime role. In: PO_REGION, PO_MODEL_ID, PO_TEST_STRING, PO_RUNTIME_ROLE_NAME.
# The reply is compared here and never printed.
echo "CHECK=dc37-converse"
result=expected
err=$(mktemp)
reply=$(aws bedrock-runtime converse --region "$PO_REGION" --model-id "$PO_MODEL_ID" \
  --messages "[{\"role\":\"user\",\"content\":[{\"text\":\"Reply with exactly $PO_TEST_STRING\"}]}]" \
  --inference-config '{"maxTokens":10}' \
  --query 'output.message.content[0].text' --output text 2>"$err")
rc=$?
code=$(sed -n 's/.*An error occurred (\([A-Za-z0-9.]*\)).*/\1/p' "$err" | head -n 1)
rm -f "$err"
echo "exit=$rc"
[ -z "$code" ] || echo "error_code=$code"
reply=$(printf '%s' "$reply" | tr -d '\r\n' | sed 's/^ *//; s/ *$//')
if [ "$rc" -eq 0 ] && [ "$reply" = "$PO_TEST_STRING" ]; then
  echo "reply_equals_test_string=yes"
else
  echo "reply_equals_test_string=no"
  result=unexpected
fi
reply=""
arn=$(aws sts get-caller-identity --region "$PO_REGION" --query Arn --output text 2>/dev/null)
echo "caller_arn=$arn"
case "$arn" in *":assumed-role/$PO_RUNTIME_ROLE_NAME/"*) ;; *) result=unexpected ;; esac
echo "RESULT=$result"
exit 0
