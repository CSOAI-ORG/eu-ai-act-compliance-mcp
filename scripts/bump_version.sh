#!/usr/bin/env bash
# bump_version.sh <new_version>
#
# Single source of truth for MCP version bumps. Updates:
#   - pyproject.toml [project].version
#   - server.json    .version + .packages[].version
#   - package.json   .version (if present)
#
# Then runs the publish_meta lint to confirm everything agrees, and
# (optionally) commits + tags.
#
# Usage:
#   ./scripts/bump_version.sh 1.5.2
#   ./scripts/bump_version.sh 1.5.2 --commit
#   ./scripts/bump_version.sh 1.5.2 --commit --tag

set -euo pipefail

NEW_VER="${1:-}"
COMMIT=0
TAG=0

shift || true
while [ $# -gt 0 ]; do
  case "$1" in
    --commit) COMMIT=1 ;;
    --tag)    TAG=1 ;;
    *)        echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ -z "$NEW_VER" ] || [[ ! "$NEW_VER" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9a-zA-Z]+)*$ ]]; then
  echo "Usage: $0 <semver> [--commit] [--tag]" >&2
  echo "Example: $0 1.5.2 --commit --tag" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYPROJECT="pyproject.toml"
SERVERJSON="server.json"
PACKAGEJSON="package.json"

if [ ! -f "$PYPROJECT" ]; then
  echo "❌ pyproject.toml not found in $ROOT" >&2
  exit 1
fi

# 1. pyproject.toml
python3 - <<PYEOF
import re, pathlib
p = pathlib.Path("$PYPROJECT")
t = p.read_text()
# Replace under [project] (could be [tool.poetry] too)
new = re.sub(r'^(version\s*=\s*)"[^"]+"', r'\g<1>"$NEW_VER"', t, count=1, flags=re.MULTILINE)
if new == t:
    raise SystemExit("❌ Could not find version= line in pyproject.toml")
p.write_text(new)
print("✓ pyproject.toml → $NEW_VER")
PYEOF

# 2. server.json
if [ -f "$SERVERJSON" ]; then
  python3 - <<PYEOF
import json, pathlib
p = pathlib.Path("$SERVERJSON")
d = json.loads(p.read_text())
d["version"] = "$NEW_VER"
for pkg in d.get("packages", []):
    pkg["version"] = "$NEW_VER"
p.write_text(json.dumps(d, indent=2) + "\n")
print("✓ server.json → $NEW_VER")
PYEOF
fi

# 3. package.json (optional — only npm-published MCPs)
if [ -f "$PACKAGEJSON" ]; then
  python3 - <<PYEOF
import json, pathlib
p = pathlib.Path("$PACKAGEJSON")
d = json.loads(p.read_text())
d["version"] = "$NEW_VER"
p.write_text(json.dumps(d, indent=2) + "\n")
print("✓ package.json → $NEW_VER")
PYEOF
fi

# 4. Verify agreement
if [ -f "$ROOT/scripts/lint_publish_meta.py" ]; then
  python3 "$ROOT/scripts/lint_publish_meta.py"
fi

# 5. Optional commit / tag
if [ $COMMIT -eq 1 ]; then
  /usr/bin/git add "$PYPROJECT" "$SERVERJSON" 2>/dev/null || true
  [ -f "$PACKAGEJSON" ] && /usr/bin/git add "$PACKAGEJSON"
  /usr/bin/git commit -m "chore(release): bump to v$NEW_VER" || echo "(no changes to commit)"
fi
if [ $TAG -eq 1 ]; then
  /usr/bin/git tag -a "v$NEW_VER" -m "v$NEW_VER" || echo "(tag exists)"
fi

echo
echo "Done — bumped to $NEW_VER"
echo "Next steps:"
echo "  1. ./scripts/publish_all.sh        # PyPI + npm + Anthropic Registry"
echo "  2. /usr/bin/git push --follow-tags # push commit + tag if --commit --tag"
