#!/usr/bin/env bash
# PostToolUse(Edit|Write|MultiEdit): auto-format and lint-fix the edited file
# through the Vite+ (vp) toolchain. Silent and non-blocking.
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

# Only touch source files the toolchain understands.
case "$file" in
  *.vue|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.css) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0

# Hooks run in a fresh shell that doesn't source the interactive profile;
# make sure the vp binary is reachable before using it.
export PATH="$HOME/.vite-plus/bin:$PATH"
command -v vp >/dev/null 2>&1 || exit 0

vp fmt "$file" --write >/dev/null 2>&1 || true

# Lint autofix for JS/TS/Vue (not CSS).
case "$file" in
  *.vue|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs)
    vp lint "$file" --fix >/dev/null 2>&1 || true
    ;;
esac

exit 0
