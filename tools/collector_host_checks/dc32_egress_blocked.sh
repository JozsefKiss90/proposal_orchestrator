# DC-32: requests to public endpoints from the host fail.
# In: PO_EGRESS_HOSTS (space-separated host names). curl exit 0 would mean a connection was made.
echo "CHECK=dc32-egress-blocked"
result=expected
for h in $PO_EGRESS_HOSTS; do
  curl -s -o /dev/null --connect-timeout 5 --max-time 10 "https://$h/" 2>/dev/null
  rc=$?
  echo "host=$h curl_exit=$rc"
  [ "$rc" -ne 0 ] || result=unexpected
done
echo "RESULT=$result"
exit 0
