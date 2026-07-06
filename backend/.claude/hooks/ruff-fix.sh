#!/usr/bin/env bash
# PostToolUse(Edit|Write): auto-format and lint-fix the edited Python file.
# Silent and non-blocking — keeps the tree clean without prompting.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null || true)

case "$file" in
  *.py) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

proj="${CLAUDE_PROJECT_DIR:-$(pwd)}"
ruff="$proj/.venv/bin/ruff"
[ -x "$ruff" ] || ruff="ruff"

"$ruff" format "$file" >/dev/null 2>&1 || true
"$ruff" check --fix "$file" >/dev/null 2>&1 || true
exit 0
