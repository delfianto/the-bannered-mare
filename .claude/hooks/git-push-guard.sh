#!/usr/bin/env bash
# PreToolUse(Bash): enforce the git policy — commit freely on `main`, but
# `git push` needs explicit user approval. Commit/stage/inspect pass through.
# Repo-wide (no path scoping needed).
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || true)

if printf '%s' "$cmd" | grep -qE '(^|[^[:alnum:]_])git[[:space:]]+push([^[:alnum:]_]|$)'; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Repo policy: git push needs explicit user approval."}}'
  exit 0
fi
exit 0
