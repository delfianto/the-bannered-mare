#!/usr/bin/env bash
# =============================================================================
# The Bannered Mare — Generate OpenAPI Schema
#
# Outputs openapi.json at the repository root — the shared API contract the
# frontend consumes via `bun run api:gen`.
#
# Usage:
#   ./scripts/openapi.sh                    # Default: <repo-root>/openapi.json
#   ./scripts/openapi.sh docs/openapi.json  # Custom path (relative to backend/)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$BACKEND_ROOT"

# Find python
if [ -f ".venv/bin/python3" ]; then
  PYTHON=".venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "Error: python3 not found."
  exit 1
fi

OUTPUT="${1:-$REPO_ROOT/openapi.json}"

$PYTHON -c "
from src.core.utils.openapi import generate_openapi_schema
generate_openapi_schema('$OUTPUT')
"
