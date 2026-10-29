# DC-31: no Claude CLI binary on the host.
# In: PO_HOME_DIRS (space-separated paths).
echo "CHECK=dc31-no-claude-cli"
result=expected
if command -v claude >/dev/null 2>&1; then
  echo "on_path=yes"
  result=unexpected
else
  echo "on_path=no"
fi
for p in /usr/local/bin/claude /usr/bin/claude; do
  if [ -e "$p" ]; then echo "path=$p present=yes"; result=unexpected; else echo "path=$p present=no"; fi
done
for h in $PO_HOME_DIRS; do
  for p in "$h/.local/bin/claude" "$h/.npm-global/bin/claude" "$h/.claude/local/claude"; do
    if [ -e "$p" ]; then echo "path=$p present=yes"; result=unexpected; else echo "path=$p present=no"; fi
  done
done
found=$(find / -xdev \( -path /proc -o -path /sys \) -prune -o -type f -name claude -perm -u+x -print 2>/dev/null | wc -l)
echo "executables_named_claude=$found"
[ "$found" = "0" ] || result=unexpected
echo "RESULT=$result"
exit 0
