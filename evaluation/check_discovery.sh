#!/usr/bin/env bash
# Check that Claude Code discovers the bug-hunter skill and both subagents.
#
#   evaluation/check_discovery.sh [directory]     (default: this repository)
#
# Starts Claude Code non-interactively in the directory and reads the
# session's init event, which lists every skill, slash command and agent
# Claude Code loaded. Also validates the frontmatter of the skill and agent
# files. Discovery is reported even if you are not signed in, because the
# init event is written before any model call.
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$(cd "${1:-$repo_root}" && pwd)"

if ! command -v claude >/dev/null 2>&1; then
  echo "FAIL: the claude command is not on PATH" >&2
  exit 1
fi

echo "Claude Code: $(claude --version 2>/dev/null)"
echo "Directory:   $target"
echo

status=0
for dir in .claude/skills .claude/agents; do
  if claude plugin validate "$target/$dir" >/dev/null 2>&1; then
    echo "ok    frontmatter valid: $dir"
  else
    echo "FAIL  frontmatter problem in $dir (run: claude plugin validate $dir)"
    status=1
  fi
done

events="$(mktemp)"
trap 'rm -f "$events"' EXIT
(cd "$target" && claude -p "Reply with OK" --output-format stream-json --verbose --max-turns 1 \
  < /dev/null > "$events" 2>/dev/null)

python3 - "$events" <<'EOF' || status=1
import json, sys

init = None
for line in open(sys.argv[1], encoding="utf-8"):
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if event.get("type") == "system" and event.get("subtype") == "init":
        init = event
        break

if init is None:
    print("FAIL  Claude Code did not report a session init event")
    sys.exit(1)

checks = [
    ("skill bug-hunter", "bug-hunter" in init.get("skills", [])),
    ("slash command /bug-hunter", "bug-hunter" in init.get("slash_commands", [])),
    ("subagent bug-scout", "bug-scout" in init.get("agents", [])),
    ("subagent test-engineer", "test-engineer" in init.get("agents", [])),
]
failed = False
for label, found in checks:
    print(("ok    " if found else "FAIL  ") + "discovered: " + label)
    failed = failed or not found
sys.exit(1 if failed else 0)
EOF

echo
if [ "$status" -eq 0 ]; then
  echo "All discovery checks passed."
else
  echo "Some checks failed."
fi
exit "$status"
