# DC-15: no long-term access key on the host, in files or in any process environment.
# In: PO_HOME_DIRS, PO_ENV_FILES (space-separated paths).
# The variable and file-key names, and the long-term key-id prefix, are assembled here at run time;
# only counts are printed.
echo "CHECK=dc15-no-long-term-keys"
result=expected
v1="AWS_ACCESS_KEY_ID"
v2="AWS_SE""CRET_ACCESS_KEY"
f1="aws_access_key_id"
f2="aws_se""cret_access_key"
kp="AK""IA"
pattern="$v1|$v2|$f1|$f2|$kp[0-9A-Z]{16}"
scan_file() {
  if [ ! -e "$1" ]; then
    echo "file=$1 present=no"
    return
  fi
  n=$(grep -c -E "$pattern" "$1" 2>/dev/null)
  echo "file=$1 present=yes matches=${n:-0}"
  [ "${n:-0}" = "0" ] || result=unexpected
}
for h in $PO_HOME_DIRS; do
  for f in .aws/credentials .aws/config .bashrc .bash_profile .profile; do
    scan_file "$h/$f"
  done
done
for f in $PO_ENV_FILES /etc/profile.d/*; do
  scan_file "$f"
done
procs=0
hits=0
for e in /proc/[0-9]*/environ; do
  [ -r "$e" ] || continue
  procs=$((procs + 1))
  n=$(tr '\0' '\n' < "$e" 2>/dev/null | grep -c -E "^($v1|$v2)=")
  [ "${n:-0}" = "0" ] || hits=$((hits + 1))
done
echo "process_environments_scanned=$procs processes_with_key_variables=$hits"
[ "$hits" = "0" ] || result=unexpected
type=$(aws configure list 2>/dev/null | awk '$1 == "access_key" {print $3}')
echo "cli_credential_source=$type"
[ "$type" = "iam-role" ] || result=unexpected
echo "RESULT=$result"
exit 0
