# DC-17: a Bedrock call to an unapproved Region fails from the host.
# In: PO_NEGATIVE_REGION, PO_MODEL_ID, PO_TEST_STRING. No reply text is printed.
echo "CHECK=dc17-negative-region"
export AWS_MAX_ATTEMPTS=1
err=$(mktemp)
aws bedrock-runtime converse --region "$PO_NEGATIVE_REGION" --model-id "$PO_MODEL_ID" \
  --messages "[{\"role\":\"user\",\"content\":[{\"text\":\"Reply with exactly $PO_TEST_STRING\"}]}]" \
  --inference-config '{"maxTokens":10}' --cli-connect-timeout 5 --cli-read-timeout 10 \
  --query stopReason --output text >/dev/null 2>"$err"
rc=$?
code=$(sed -n 's/.*An error occurred (\([A-Za-z0-9.]*\)).*/\1/p' "$err" | head -n 1)
if grep -q -i -E 'could not connect|connect timeout|timed out' "$err"; then
  kind=connection_failed
elif [ -n "$code" ]; then
  kind="aws_error:$code"
elif [ "$rc" -ne 0 ]; then
  kind=other_failure
else
  kind=none
fi
rm -f "$err"
echo "negative_region=$PO_NEGATIVE_REGION"
echo "exit=$rc"
echo "failure_kind=$kind"
if [ "$rc" -ne 0 ]; then echo "RESULT=expected"; else echo "RESULT=unexpected"; fi
exit 0
