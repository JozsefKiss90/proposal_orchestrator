#!/usr/bin/env bash
# Install the offline bundle on the private host (AN12, ADR-001 Decision 8).
#
# Run from anywhere, after extracting the tarball:
#   bash <bundle>/app/deploy/install_host.sh /opt/msca-dn-anonymisation
#
# Nothing here reaches a network. The interpreter and every wheel are checked
# against SHA256SUMS before use; pip installs with --no-index and
# --require-hashes from the bundled wheels alone; the last step verifies the
# installed tree against bundle_manifest.json. The ADR-001 environment checks
# are a separate step, run with the production environment loaded.
set -euo pipefail

TARGET="${1:?usage: install_host.sh TARGET_DIR}"
BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Checking the interpreter and wheels against SHA256SUMS ==="
(cd "$BUNDLE" && sha256sum --check --strict SHA256SUMS)

if [ -e "$TARGET" ]; then
  echo "refused: $TARGET exists; install into a new directory" >&2
  exit 2
fi
mkdir -p "$TARGET"

echo "=== Extracting the interpreter ==="
tar xzf "$BUNDLE"/python/*.tar.gz -C "$TARGET"
PY="$TARGET/python/bin/python3"
"$PY" --version

echo "=== Copying the application ==="
cp -a "$BUNDLE/app" "$TARGET/app"

echo "=== Installing the pinned wheels (no index, hashes required) ==="
"$PY" -m pip install --no-index --require-hashes --no-cache-dir \
  --find-links "$BUNDLE/wheels" -r "$TARGET/app/deploy/requirements-host.txt"

echo "=== Verifying the installed files ==="
cd "$TARGET/app"
"$PY" - <<'VERIFY'
import sys
from pathlib import Path
from runner import offline_bundle as ob
record = ob.verify(Path.cwd())
files = next(c for c in record["checks"] if c["check"] == "files")
print(files["detail"])
sys.exit(0 if files["passed"] else 1)
VERIFY

echo "=== INSTALL_COMPLETE: run 'python -m runner.offline_bundle verify' with the production environment loaded ==="
