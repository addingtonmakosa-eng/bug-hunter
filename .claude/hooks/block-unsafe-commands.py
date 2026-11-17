#!/usr/bin/env python3
"""PreToolUse hook: block a short list of unsafe shell commands.

Claude Code runs this before every Bash tool call (see .claude/settings.json)
and passes the call as JSON on stdin. Exit code 2 blocks the call and shows
the message on stderr to Claude. Exit code 0 lets the normal permission flow
continue; it does not approve anything.

This is a deterministic backstop for the rules in the bug-hunter skill. It is
a deny-list, so it cannot catch every dangerous command. Claude Code's own
permission prompts remain the main control.
"""

import json
import re
import sys

# (pattern, reason). Patterns are matched against each command segment.
RULES = [
    (r"\brm\s+(-[a-zA-Z]*[rRf][a-zA-Z]*\b|--recursive\b|--force\b)", "recursive or forced file deletion"),
    (r"\bgit\s+reset\s+.*--hard\b", "git reset --hard discards uncommitted work"),
    (r"\bgit\s+clean\b", "git clean deletes untracked files"),
    (r"\bgit\s+checkout\s+(--\s|\.\s*$|.*\s--\s)", "git checkout of paths discards uncommitted changes"),
    (r"\bgit\s+restore\b(?!.*--staged)", "git restore discards uncommitted changes"),
    (r"\bgit\s+stash\s+(drop|clear)\b", "dropping stashes destroys saved work"),
    (r"\bgit\s+push\b.*(\s--force\b|\s--force-with-lease\b|\s-f\b)", "force push rewrites remote history"),
    (r"\bgit\s+branch\s+.*-D\b", "force-deleting a branch can lose commits"),
    (r"^\s*sudo\b", "commands must not run with elevated privileges"),
    (r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba|z)?sh\b", "piping a download into a shell"),
    (r"\bchmod\s+(-R\s+)?777\b", "world-writable permissions"),
    (r"\b(mkfs|fdisk)\b|\bdd\s+.*\bof=/dev/", "disk-level operation"),
    (r"\b(pip3?|python3?\s+-m\s+pip)\s+(install|uninstall)\b", "dependency changes need the user's approval"),
    (r"\b(npm|pnpm|yarn)\s+(install|add|remove|uninstall|i)\b", "dependency changes need the user's approval"),
    (r"\b(alembic\s+(upgrade|downgrade)|manage\.py\s+migrate|prisma\s+migrate\s+(deploy|reset)|rails\s+db:(migrate|drop|reset))\b",
     "database migrations need the user's approval"),
    (r"\bdrop\s+(table|database|schema)\b", "destructive SQL"),
    (r"^\s*(printenv|env)\s*$", "printing the environment can expose credentials"),
    (r"\b(cat|less|more|head|tail)\s+[^|;&]*(\.env\b|id_rsa|id_ed25519|\.pem\b|credentials)", "reading credential files"),
    (r"\b(terraform\s+(apply|destroy)|kubectl\s+(apply|delete)|docker\s+system\s+prune)\b", "infrastructure changes"),
]

COMPILED = [(re.compile(pattern, re.IGNORECASE), reason) for pattern, reason in RULES]
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\n")


def find_violation(command):
    """Return the reason the command is blocked, or None if it is allowed."""
    for segment in SEGMENT_SPLIT.split(command):
        for pattern, reason in COMPILED:
            if pattern.search(segment):
                return reason
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0  # Not a hook payload we understand: do not interfere.

    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command", "")
    if not isinstance(command, str):
        return 0

    reason = find_violation(command)
    if reason is None:
        return 0

    print(
        f"Blocked by the Bug Hunter safety hook: {reason}. "
        "Do not retry with a different spelling. If this command is really needed, "
        "explain why and ask the user to run it themselves.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
