# scripts/

Repo-level dev tooling. The shell scripts locate `backend/` themselves, so they
run from anywhere; the Python card tools run under the backend virtualenv.

## Backend tooling

| Script | Purpose |
|--------|---------|
| `openapi.sh` | Regenerate the root `openapi.json` contract from the FastAPI app. |
| `init-backend-db.sh` | Provision a local PostgreSQL database, role, and the `vchord` (VectorChord) extension, then run migrations. |
| `start-backend.sh` | Run the backend server (uvicorn — `--reload` in dev, `--prod` for workers). |

## Character-card tools

General-purpose TavernCard (V1/V2) utilities. Run with the backend venv, e.g.
`backend/.venv/bin/python scripts/analyze_card.py …`. `import`/`export` also need
the backend env (`.env` / `DATABASE_URL`) and a migrated database.

| Script | Purpose |
|--------|---------|
| `analyze_card.py` | Decode a card and print its normalized fields — no DB. Takes files, globs, or a directory; `--json` dumps the full card. |
| `import_card.py` | Import card(s) into the DB — character + lorebook (from `character_book`) + avatar. Takes files or a directory. |
| `export_card.py` | Export a DB character (`--name` or `--id`) as a PNG or JSON card (`--format`, `-o`). |

Sample cards to try these on live in [`../characters/`](../characters/README.md).
