# The Bannered Mare — task runner (https://github.com/casey/just)
# One entrypoint for every surface: database, backend, frontend, docs.
# Run `just` (or `just --list`) to see everything, grouped by surface.
#
# Ports:  backend 8000 · frontend dev 5173 · frontend preview 4173 · docs 5174
# Docs is pinned to 5174 so it can run alongside the frontend (both default to 5173).

set shell := ["bash", "-c"]

backend_dir := "backend"
frontend_dir := "frontend"
docs_dir := "docs"
seed_dir := "characters"

be_port := "8000"
fe_port := "5173"
fe_preview_port := "4173"
docs_port := "5174"

# Show all recipes (default).
default:
    @just --list

# ─────────────────────────────── database ───────────────────────────────

# Initialize the database — create role/db, install VectorChord, run migrations (interactive).
[group('database')]
db-init:
    ./scripts/init-backend-db.sh

# Initialize non-interactively (env vars / defaults) — for CI / first boot.
[group('database')]
db-init-auto:
    ./scripts/init-backend-db.sh --auto

# DROP and recreate the database, then re-migrate. Destroys all data (asks first).
[group('database')]
db-reset:
    ./scripts/init-backend-db.sh --reset

# Validate migrations — error if the models have drifted from the latest migration.
[group('database')]
db-check:
    cd {{ backend_dir }} && .venv/bin/alembic check

# Show migration status — current DB revision, latest heads, and recent history.
[group('database')]
db-status:
    cd {{ backend_dir }} && .venv/bin/alembic current && echo "── heads ──" && .venv/bin/alembic heads && echo "── history ──" && .venv/bin/alembic history

# Run migrations — upgrade the database to the latest revision.
[group('database')]
db-migrate:
    cd {{ backend_dir }} && .venv/bin/alembic upgrade head

# Autogenerate a new migration from model changes:  just db-revision "add foo table"
[group('database')]
db-revision message:
    cd {{ backend_dir }} && .venv/bin/alembic revision --autogenerate -m "{{ message }}"

# Back up the database to backups/candlekeep-<timestamp>.dump (pg_dump custom format).
[group('database')]
db-backup:
    #!/usr/bin/env bash
    set -euo pipefail
    url=$(grep -E '^DATABASE_URL=' {{ backend_dir }}/.env | head -1 | cut -d= -f2-)
    [ -n "$url" ] || { echo "DATABASE_URL not found in {{ backend_dir }}/.env"; exit 1; }
    mkdir -p backups
    out="backups/candlekeep-$(date +%Y%m%d-%H%M%S).dump"
    echo "Backing up → $out"
    pg_dump "$url" --format=custom --file "$out"
    echo "✓ $out ($(du -h "$out" | cut -f1))"

# Restore the database from a dump:  just db-restore backups/candlekeep-XXXX.dump
[group('database')]
db-restore file:
    #!/usr/bin/env bash
    set -euo pipefail
    url=$(grep -E '^DATABASE_URL=' {{ backend_dir }}/.env | head -1 | cut -d= -f2-)
    [ -n "$url" ] || { echo "DATABASE_URL not found in {{ backend_dir }}/.env"; exit 1; }
    echo "⚠  Restoring {{ file }} → $url  (existing objects are dropped first)"
    pg_restore --clean --if-exists --no-owner --dbname "$url" "{{ file }}"
    echo "✓ restored"

# Seed character cards into the DB (default: ./characters).  e.g. just db-seed characters/foo.png
[group('database')]
db-seed path=seed_dir:
    {{ backend_dir }}/.venv/bin/python scripts/import_card.py {{ path }}

# ─────────────────────────────── backend ────────────────────────────────

# Run the backend in dev mode (uvicorn --reload) on :8000.
[group('backend')]
be-dev:
    ./scripts/start-backend.sh

# Run the backend in prod mode (uvicorn, 4 workers, no reload) on :8000.
[group('backend')]
be-prod:
    ./scripts/start-backend.sh --prod

# Stop the backend.
[group('backend')]
be-stop: (kill-port be_port "backend")

# ─────────────────────────────── frontend ───────────────────────────────

# Run the frontend in dev mode (talks to the real backend) on :5173.
[group('frontend')]
fe-dev:
    cd {{ frontend_dir }} && bun run dev --port {{ fe_port }}

# Run the frontend in dev mode with the MSW mock harness (no backend needed) on :5173.
[group('frontend')]
fe-mock:
    cd {{ frontend_dir }} && bun run dev:mock --port {{ fe_port }}

# Build + serve the production frontend bundle on :4173.
[group('frontend')]
fe-prod:
    cd {{ frontend_dir }} && bun run build && bun run preview --port {{ fe_preview_port }}

# Stop the frontend (dev + preview).
[group('frontend')]
fe-stop: (kill-port fe_port "frontend (dev)") (kill-port fe_preview_port "frontend (preview)")

# ───────────────────────────────── docs ─────────────────────────────────

# Run the documentation site (VitePress dev) on :5174.
[group('docs')]
docs-dev:
    cd {{ docs_dir }} && bun run docs:dev --port {{ docs_port }}

# Stop the docs server.
[group('docs')]
docs-stop: (kill-port docs_port "docs")

# ───────────────────────────────── stop ─────────────────────────────────

# Show which dev services are currently running.
[group('stop')]
status:
    #!/usr/bin/env bash
    set -uo pipefail
    echo "The Bannered Mare — dev process status"
    _row() {
      local pids; pids=$(lsof -ti tcp:"$1" 2>/dev/null || true)
      if [ -n "$pids" ]; then printf '  ● %-20s :%s  RUNNING (pid %s)\n' "$2" "$1" "$(echo $pids | tr "\n" " ")"
      else printf '  ○ %-20s :%s  stopped\n' "$2" "$1"; fi
    }
    _row {{ be_port }} backend
    _row {{ fe_port }} "frontend (dev)"
    _row {{ fe_preview_port }} "frontend (preview)"
    _row {{ docs_port }} docs

# Stop EVERYTHING — backend, frontend, docs — then sweep for stray dev processes.
[group('stop')]
stop-all: be-stop fe-stop docs-stop
    #!/usr/bin/env bash
    set -uo pipefail
    echo ""
    echo "Sweeping for stray dev processes…"
    found=0
    for pat in "uvicorn src.main:app" "vp dev" "vp preview" "vitepress"; do
      pids=$(pgrep -f "$pat" 2>/dev/null || true)
      if [ -n "$pids" ]; then
        echo "  ✓ killing '$pat' (pid $(echo $pids | tr "\n" " "))"
        pkill -f "$pat" 2>/dev/null || true
        found=1
      fi
    done
    [ "$found" -eq 0 ] && echo "  · none found"
    echo "Done."

# ──────────────────────────────── helpers ───────────────────────────────

# (internal) Kill whatever is listening on a TCP port.
[private]
kill-port port name:
    #!/usr/bin/env bash
    set -uo pipefail
    pids=$(lsof -ti tcp:{{ port }} 2>/dev/null || true)
    if [ -n "$pids" ]; then
      echo "  ✓ stopping {{ name }} — port {{ port }} (pid $(echo $pids | tr "\n" " "))"
      kill $pids 2>/dev/null || true
    else
      echo "  · {{ name }} — nothing on port {{ port }}"
    fi
