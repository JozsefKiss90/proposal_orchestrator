# DC-33 to DC-35 (and the runtime half of DC-21): the R9 launcher reads the runtime secret on the host
# and starts a child that prints the configuration's key names and SHA-256, never a value.
# In: PO_BUNDLE_DIR, PO_BUNDLE_PYTHON, PO_REGION, PO_SECRET_ID, PO_EXPECTED_SHA256, PO_CONFIG_KEYS.
echo "CHECK=dc33-35-launcher-config"
if ! cd "$PO_BUNDLE_DIR" 2>/dev/null; then
  echo "bundle_dir=absent"
  echo "RESULT=unexpected"
  exit 0
fi
out=$("$PO_BUNDLE_PYTHON" -m runner.host_env --region "$PO_REGION" --secret-id "$PO_SECRET_ID" -- \
  "$PO_BUNDLE_PYTHON" -c '
import hashlib, json, os
keys = os.environ["PO_CONFIG_KEYS"].split()
present = [k for k in keys if k in os.environ]
obj = {k: os.environ[k] for k in present}
print("key_names=" + ",".join(sorted(present)))
print("sha256=" + hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest())
' 2>&1)
rc=$?
echo "launcher_exit=$rc"
printf '%s\n' "$out" | grep -E '^(key_names|sha256)=' || true
printf '%s\n' "$out" | grep -E '^host_env' | head -n 1 || true
sha=$(printf '%s\n' "$out" | sed -n 's/^sha256=//p')
if [ "$rc" -eq 0 ] && [ "$sha" = "$PO_EXPECTED_SHA256" ]; then
  echo "sha256_matches_template=yes"
  echo "RESULT=expected"
else
  echo "sha256_matches_template=no"
  echo "RESULT=unexpected"
fi
exit 0
