#!/usr/bin/env bash
# Stop: enforce the CLAUDE.md QA gate — block finishing while vue-tsc reports
# type errors. The stop_hook_active guard prevents an infinite loop.
set -euo pipefail

input=$(cat)
active=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('stop_hook_active',False))" 2>/dev/null || echo False)
[ "$active" = "True" ] && exit 0

proj="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$proj" || exit 0

# Prefer the project-local binary. If deps aren't installed, don't block.
tsc="$proj/node_modules/.bin/vue-tsc"
[ -x "$tsc" ] || exit 0

# vue-tsc exits non-zero when type errors exist.
if ! out=$("$tsc" --noEmit 2>&1); then
  printf '%s\n' "$out" | tail -n 40 >&2
  echo "vue-tsc reports type error(s) — fix before finishing (CLAUDE.md QA gate)." >&2
  exit 2
fi
exit 0
