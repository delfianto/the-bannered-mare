#!/usr/bin/env bash
# PreToolUse(Bash): enforce CLAUDE.md "no git commits unless the user asked".
# commit/push require explicit user approval via permission prompt;
# staging and inspection commands pass through.
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || true)

if printf '%s' "$cmd" | grep -qE '(^|[^[:alnum:]_])git[[:space:]]+(commit|push)([^[:alnum:]_]|$)'; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"CLAUDE.md: git commit/push needs explicit user approval."}}'
  exit 0
fi
exit 0
