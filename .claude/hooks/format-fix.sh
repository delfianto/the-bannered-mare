#!/usr/bin/env bash
# PostToolUse(Edit|Write|MultiEdit): auto-format and lint-fix the edited file.
# Silent and non-blocking — keeps the tree clean without prompting.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null || true)

[ -n "$file" ] || exit 0
[ -f "$file" ] || exit 0

# Never reformat generated / declaration files.
case "$file" in
  *.d.ts) exit 0 ;;
  */src/api/schema.d.ts) exit 0 ;;
esac

proj="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Formatter — oxfmt is a standalone binary resolved from PATH.
case "$file" in
  *.vue|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.css)
    if command -v oxfmt >/dev/null 2>&1; then
      oxfmt "$file" >/dev/null 2>&1 || true
    fi
    ;;
esac

# Linter with autofix — JS/TS/Vue only (prefer the project-local binary).
oxlint="$proj/node_modules/.bin/oxlint"
[ -x "$oxlint" ] || oxlint="oxlint"
case "$file" in
  *.vue|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs)
    "$oxlint" --fix "$file" >/dev/null 2>&1 || true
    ;;
esac

exit 0
