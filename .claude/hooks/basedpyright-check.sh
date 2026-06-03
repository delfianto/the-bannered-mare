#!/usr/bin/env bash
# Stop: enforce the CLAUDE.md QA gate — block finishing while basedpyright
# reports errors. The stop_hook_active guard prevents an infinite loop.
set -euo pipefail

input=$(cat)
active=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('stop_hook_active',False))" 2>/dev/null || echo False)
[ "$active" = "True" ] && exit 0

proj="${CLAUDE_PROJECT_DIR:-$(pwd)}"
# Prefer the venv binary, but only if it actually runs — a venv with stale
# shebangs (e.g. after a directory rename) would otherwise pass the gate silently.
bp="basedpyright"
if [ -x "$proj/.venv/bin/basedpyright" ] && "$proj/.venv/bin/basedpyright" --version >/dev/null 2>&1; then
  bp="$proj/.venv/bin/basedpyright"
fi

out=$("$bp" --project "$proj" 2>&1) || true
errs=$(printf '%s' "$out" | grep -oE '[0-9]+ error' | head -1 | grep -oE '^[0-9]+' || echo 0)

if [ "${errs:-0}" -gt 0 ]; then
  printf '%s\n' "$out" | tail -n 40 >&2
  echo "basedpyright reports ${errs} error(s) — fix before finishing (CLAUDE.md QA gate)." >&2
  exit 2
fi
exit 0
