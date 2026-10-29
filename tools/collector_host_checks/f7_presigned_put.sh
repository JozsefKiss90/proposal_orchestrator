# F7: a presigned PUT to a bucket outside the account is refused from the host.
# In: PO_F7_URL. The URL, the bucket and the response body are never printed: only the HTTP status,
# the S3 error code and whether the message names a VPC endpoint policy.
echo "CHECK=f7-presigned-put"
body=$(mktemp)
status=$(curl -s -o "$body" -w '%{http_code}' -X PUT --data-binary 'F7-negative-test' \
  --connect-timeout 5 --max-time 15 "$PO_F7_URL" 2>/dev/null)
rc=$?
code=$(sed -n 's:.*<Code>\([A-Za-z]*\)</Code>.*:\1:p' "$body" | head -n 1)
if grep -q -i 'VPC endpoint policy' "$body"; then vpce=yes; else vpce=no; fi
rm -f "$body"
echo "curl_exit=$rc"
echo "http_status=$status"
echo "error_code=$code"
echo "message_names_vpc_endpoint_policy=$vpce"
case "$status" in
  2*) echo "RESULT=unexpected" ;;
  *) echo "RESULT=expected" ;;
esac
exit 0
