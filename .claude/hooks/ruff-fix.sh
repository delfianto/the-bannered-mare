#!/usr/bin/env bash
# PostToolUse(Edit|Write|MultiEdit): auto-format and lint-fix edited *backend*
# Python files via ruff. Path-scoped to backend/ so it stays inert for the
# frontend and docs halves when Claude runs from the repo root. Non-blocking.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null || true)

# Only backend Python files (absolute or repo-relative path).
case "$file" in
  */backend/*.py|backend/*.py) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
ruff="$root/backend/.venv/bin/ruff"
[ -x "$ruff" ] || ruff="ruff"

"$ruff" format "$file" >/dev/null 2>&1 || true
"$ruff" check --fix "$file" >/dev/null 2>&1 || true
exit 0
