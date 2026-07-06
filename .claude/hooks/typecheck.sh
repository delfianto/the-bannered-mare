#!/usr/bin/env bash
# Stop: enforce the frontend QA gate — block finishing while vue-tsc reports type
# errors in frontend/. Runs against $CLAUDE_PROJECT_DIR/frontend so it works when
# Claude is launched from the repo root. stop_hook_active guard prevents a loop.
set -euo pipefail

input=$(cat)
active=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('stop_hook_active',False))" 2>/dev/null || echo False)
[ "$active" = "True" ] && exit 0

root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
proj="$root/frontend"
[ -d "$proj" ] || exit 0
cd "$proj" || exit 0

# Prefer the project-local binary. If deps aren't installed, don't block.
tsc="$proj/node_modules/.bin/vue-tsc"
[ -x "$tsc" ] || exit 0

# vue-tsc exits non-zero when type errors exist.
if ! out=$("$tsc" --noEmit 2>&1); then
  printf '%s\n' "$out" | tail -n 40 >&2
  echo "vue-tsc reports type error(s) in frontend/ — fix before finishing (frontend QA gate)." >&2
  exit 2
fi
exit 0
