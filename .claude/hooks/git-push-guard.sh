#!/usr/bin/env bash
# PreToolUse(Bash): git push policy.
#   - normal `git push`  -> auto-approved (no yes/no prompt)
#   - force-y pushes      -> require explicit approval (they rewrite remote history)
# `git push --force` / `-f` are additionally hard-denied in settings.json.
# Any non-push Bash command is left untouched (deferred to the permission rules).
# Repo-wide (no path scoping needed).
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || true)

# Not a `git push` invocation → defer to normal permission handling.
printf '%s' "$cmd" | grep -qE '(^|[^[:alnum:]_])git[[:space:]]+push([^[:alnum:]_]|$)' || exit 0

# Force-y push (--force, --force-with-lease/-if-includes, a -f short-flag cluster,
# or a +refspec) → still ask. Errs toward asking when in doubt.
if printf '%s' "$cmd" | grep -qE '(--force|--force-with-lease|--force-if-includes|(^|[[:space:]])-[[:alnum:]]*f([[:space:]]|$)|[[:space:]]\+[^[:space:]]+)'; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Force push rewrites remote history — confirm."}}'
  exit 0
fi

# Normal push → auto-approve, no prompt.
printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Repo policy: normal git push is auto-approved."}}'
exit 0
