#!/usr/bin/env bash
# Create an isolated copy of the broken demo app for a Bug Hunter run.
#
#   evaluation/make_sandbox.sh <destination> [--no-skill]
#
# The sandbox contains demo-app/ exactly as committed in this repository
# (still broken), plus .claude/ with the skill, subagents and safety hook.
# It deliberately leaves out docs/, DEMO.md, README.md and evaluation/, which
# describe the planted defects, so the agent cannot read the answer key.
#
# --no-skill leaves .claude/ out, for the "Claude Code without Bug Hunter"
# comparison run.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <destination> [--no-skill]" >&2
  exit 64
fi

dest="$1"
with_skill=1
if [ "${2:-}" = "--no-skill" ]; then
  with_skill=0
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -e "$dest" ] && [ -n "$(ls -A "$dest" 2>/dev/null)" ]; then
  echo "error: $dest already exists and is not empty; choose a new directory" >&2
  exit 1
fi

mkdir -p "$dest"
dest="$(cd "$dest" && pwd)"

# Committed state only, so a repaired working copy never leaks into a sandbox.
git -C "$repo_root" archive HEAD demo-app | tar -x -C "$dest"
if [ "$with_skill" -eq 1 ]; then
  git -C "$repo_root" archive HEAD .claude | tar -x -C "$dest"
fi

cat > "$dest/.gitignore" <<'EOF'
__pycache__/
.pytest_cache/
*.pyc
EOF

git -C "$dest" init -q -b main
git -C "$dest" add -A
git -C "$dest" -c user.name="Bug Hunter Sandbox" -c user.email="sandbox@example.invalid" \
  -c commit.gpgsign=false commit -q -m "Baseline: broken demo app"
git -C "$dest" tag baseline

echo "Sandbox ready: $dest"
if [ "$with_skill" -eq 1 ]; then
  echo "Next: cd \"$dest\" && claude    then type: /bug-hunter"
else
  echo "Next: cd \"$dest\" && claude    then give the plain task prompt from docs/EVALUATION.md"
fi
