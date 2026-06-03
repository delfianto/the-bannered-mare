#!/usr/bin/env bash
# PreToolUse(Bash): enforce CLAUDE.md "NO GIT COMMITS". Blocks commit/push;
# staging and inspection commands pass through.
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || true)

if printf '%s' "$cmd" | grep -qE '(^|[^[:alnum:]_])git[[:space:]]+(commit|push)([^[:alnum:]_]|$)'; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"CLAUDE.md: NO GIT COMMITS — the user handles all version control. Stage/edit files only."}}'
  exit 0
fi
exit 0
