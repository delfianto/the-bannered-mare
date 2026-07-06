#!/usr/bin/env bash
# =============================================================================
# The Bannered Mare — Database Initialization Script
#
# Creates the database, installs extensions, runs migrations, and optionally
# seeds data. Designed to run once before first application start, or in a
# Docker entrypoint.
#
# Usage:
#   ./scripts/init-db.sh              # Interactive — prompts for values
#   ./scripts/init-db.sh --auto       # Non-interactive — uses env vars / defaults
#   ./scripts/init-db.sh --reset      # Drop and recreate database (destroys all data)
#   ./scripts/init-db.sh --reset --auto  # Non-interactive reset (for CI/Docker)
#
# Environment variables (all optional, have sensible defaults):
#   POSTGRES_HOST       (default: localhost)
#   POSTGRES_PORT       (default: 5432)
#   POSTGRES_USER       (default: candlekeep)
#   POSTGRES_PASSWORD   (default: candlekeep)
#   POSTGRES_DB         (default: candlekeep)
#   POSTGRES_SUPERUSER  (default: postgres)
#   PGVECTOR_ENABLED    (default: true)
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# --- Parse DATABASE_URL from .env if available ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

_parse_database_url() {
  # Extract components from DATABASE_URL=postgresql://user:pass@host:port/db
  local url="$1"
  url="${url#postgresql://}"
  url="${url#postgres://}"
  local userpass="${url%%@*}"
  local hostportdb="${url#*@}"
  DB_URL_USER="${userpass%%:*}"
  DB_URL_PASS="${userpass#*:}"
  local hostport="${hostportdb%%/*}"
  DB_URL_DB="${hostportdb#*/}"
  DB_URL_HOST="${hostport%%:*}"
  DB_URL_PORT="${hostport#*:}"
}

# Try to read DATABASE_URL from .env
if [ -f "$PROJECT_ROOT/.env" ]; then
  _env_db_url=$(grep -E "^DATABASE_URL=" "$PROJECT_ROOT/.env" 2>/dev/null | head -1 | cut -d= -f2-)
  if [ -n "$_env_db_url" ]; then
    _parse_database_url "$_env_db_url"
  fi
fi

# --- Defaults (env vars > .env > hardcoded) ---
PG_HOST="${POSTGRES_HOST:-${DB_URL_HOST:-localhost}}"
PG_PORT="${POSTGRES_PORT:-${DB_URL_PORT:-5432}}"
PG_USER="${POSTGRES_USER:-${DB_URL_USER:-candlekeep}}"
PG_PASS="${POSTGRES_PASSWORD:-${DB_URL_PASS:-candlekeep}}"
PG_DB="${POSTGRES_DB:-${DB_URL_DB:-candlekeep}}"
PG_SUPERUSER="${POSTGRES_SUPERUSER:-postgres}"
PGVECTOR="${PGVECTOR_ENABLED:-true}"
AUTO_MODE=false
RESET_MODE=false

# Parse args
for arg in "$@"; do
  case $arg in
    --auto) AUTO_MODE=true ;;
    --reset) RESET_MODE=true ;;
    *) warn "Unknown argument: $arg" ;;
  esac
done

# --- Check prerequisites ---
command -v psql >/dev/null 2>&1 || error "psql not found. Install postgresql-client."

info "The Bannered Mare — Database Initialization"
echo ""
info "Configuration:"
echo "  Host:       $PG_HOST:$PG_PORT"
echo "  Database:   $PG_DB"
echo "  App user:   $PG_USER"
echo "  Superuser:  $PG_SUPERUSER"
echo "  pgvector:   $PGVECTOR"
echo ""

if [ "$AUTO_MODE" = false ]; then
  read -rp "Continue? [Y/n] " confirm
  case "$confirm" in
    [nN]*) echo "Aborted."; exit 0 ;;
  esac
fi

# --- Helper to run SQL as superuser ---
psql_su() {
  PGPASSWORD="${POSTGRES_SUPERUSER_PASSWORD:-}" psql \
    -h "$PG_HOST" -p "$PG_PORT" -U "$PG_SUPERUSER" \
    -v ON_ERROR_STOP=1 --no-psqlrc -q "$@"
}

psql_su_db() {
  psql_su -d "$PG_DB" "$@"
}

# --- Step 0: Reset database (if --reset flag) ---
if [ "$RESET_MODE" = true ]; then
  warn "Resetting database '$PG_DB' — ALL DATA WILL BE LOST!"
  if [ "$AUTO_MODE" = false ]; then
    read -rp "Are you sure? [y/N] " confirm
    case "$confirm" in
      [yY]*) ;;
      *) echo "Aborted."; exit 0 ;;
    esac
  fi
  psql_su -d postgres -c "DROP DATABASE IF EXISTS $PG_DB;" 2>/dev/null \
    && ok "Database '$PG_DB' dropped." || warn "Could not drop database."
fi

# --- Step 1: Create role (if not exists) ---
info "Step 1: Creating role '$PG_USER' (if not exists)..."
psql_su -d postgres -c "
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$PG_USER') THEN
      CREATE ROLE $PG_USER WITH LOGIN PASSWORD '$PG_PASS';
    END IF;
  END
  \$\$;
" 2>/dev/null && ok "Role '$PG_USER' ready." || warn "Could not create role (may already exist)."

# --- Step 2: Create database (if not exists) ---
info "Step 2: Creating database '$PG_DB' (if not exists)..."
psql_su -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$PG_DB'" | grep -q 1 \
  && ok "Database '$PG_DB' already exists." \
  || { psql_su -d postgres -c "CREATE DATABASE $PG_DB OWNER $PG_USER;" && ok "Database '$PG_DB' created."; }

# --- Step 3: Grant privileges ---
info "Step 3: Granting privileges..."
psql_su_db -c "
  GRANT ALL PRIVILEGES ON DATABASE $PG_DB TO $PG_USER;
  GRANT ALL ON SCHEMA public TO $PG_USER;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $PG_USER;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $PG_USER;
" && ok "Privileges granted."

# --- Step 4: Install pgvector extension ---
if [ "$PGVECTOR" = "true" ]; then
  info "Step 4: Installing pgvector extension..."
  psql_su_db -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null \
    && ok "pgvector extension installed." \
    || warn "pgvector not available. RAG features will be disabled."
else
  info "Step 4: Skipping pgvector (PGVECTOR_ENABLED=false)."
fi

# --- Step 5: Run Alembic migrations ---
info "Step 5: Running Alembic migrations..."

# Build DATABASE_URL from components
export DATABASE_URL="postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/${PG_DB}"

cd "$PROJECT_ROOT"

# Try to find alembic in venv, fall back to system
if [ -f ".venv/bin/alembic" ]; then
  ALEMBIC=".venv/bin/alembic"
elif command -v alembic >/dev/null 2>&1; then
  ALEMBIC="alembic"
else
  error "alembic not found. Run: pip install -e '.[dev]'"
fi

$ALEMBIC upgrade head && ok "Migrations applied." || error "Migration failed."

# --- Done ---
echo ""
ok "Database initialization complete!"
echo ""
info "Connection string:"
echo "  DATABASE_URL=$DATABASE_URL"
echo ""
info "Next steps:"
echo "  1. Add DATABASE_URL to your .env file"
echo "  2. Start the server: uvicorn src.main:app --reload"
echo "  3. Open http://localhost:8000/demo"
