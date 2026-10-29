# DC-02: the service names resolve to private addresses inside the VPC.
# In: PO_REGION, PO_DNS_SERVICES (space-separated service prefixes).
echo "CHECK=dc02-private-dns"
result=expected
for svc in $PO_DNS_SERVICES; do
  name="$svc.$PO_REGION.amazonaws.com"
  addrs=$(getent ahostsv4 "$name" 2>/dev/null | awk '{print $1}' | sort -u)
  if [ -z "$addrs" ]; then
    echo "name=$name resolved=no"
    result=unexpected
    continue
  fi
  for a in $addrs; do
    if python3 -c 'import ipaddress, sys; sys.exit(0 if ipaddress.ip_address(sys.argv[1]).is_private else 1)' "$a"; then
      cls=private
    else
      cls=public
      result=unexpected
    fi
    echo "name=$name address=$a class=$cls"
  done
done
echo "RESULT=$result"
exit 0
