#!/usr/bin/env bash
# =============================================================================
# The Bannered Mare — Start Server
#
# Usage:
#   ./scripts/start.sh              # Development (auto-reload)
#   ./scripts/start.sh --prod       # Production (no reload, multiple workers)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Find uvicorn
if [ -f ".venv/bin/uvicorn" ]; then
  UVICORN=".venv/bin/uvicorn"
elif command -v uvicorn >/dev/null 2>&1; then
  UVICORN="uvicorn"
else
  echo "Error: uvicorn not found. Run: pip install -e '.[dev]'"
  exit 1
fi

# .env is loaded by pydantic-settings automatically — don't source it here
# (shell sourcing mangles JSON values like CORS_ORIGINS=["*"])
HOST="${API_HOST:-$(grep -E '^API_HOST=' .env 2>/dev/null | cut -d= -f2- || echo '0.0.0.0')}"
PORT="${API_PORT:-$(grep -E '^API_PORT=' .env 2>/dev/null | cut -d= -f2- || echo '8000')}"

if [ "${1:-}" = "--prod" ]; then
  echo "Starting The Bannered Mare (production) on $HOST:$PORT"
  exec $UVICORN src.main:app --host "$HOST" --port "$PORT" --workers 4
else
  echo "Starting The Bannered Mare (development) on $HOST:$PORT"
  echo "Demo UI: http://localhost:$PORT/demo"
  echo "API docs: http://localhost:$PORT/docs"
  exec $UVICORN src.main:app --host "$HOST" --port "$PORT" --reload
fi
