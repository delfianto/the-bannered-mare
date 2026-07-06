#!/usr/bin/env bash
# SessionStart: anchor the assistant to this project's real stack and counter
# the Rust-oriented skills present in the global skills directory.
printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Candlekeep Core is a Python 3.14 / FastAPI / SQLAlchemy 2.0 / pgvector backend. The Rust skills in ~/.claude (m01-m15, rust-*, unsafe-checker) do NOT apply here. QA gate before finishing: ruff format && ruff check --fix && basedpyright && pytest. Work on the main branch and commit freely; never git push unless the user explicitly asks."}}'
