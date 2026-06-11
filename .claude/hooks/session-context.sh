#!/usr/bin/env bash
# SessionStart: anchor the assistant to this project's real stack and counter
# unrelated skills present in the global skills directory.
printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Candlekeep UI is a Vue 3.5 / Vite 8 / TypeScript 6 (strict) SPA using Nuxt UI v4 (NOT Nuxt.js), Tailwind CSS v4, Pinia, Vue Router 5, openapi-fetch, and MSW. Runtime / package manager is Bun. Unrelated global skills in ~/.claude (Rust m01-m15, rust-*, unsafe-checker, and Python/backend helpers) do NOT apply here. QA gate before finishing: bun run lint && bun run typecheck && bun run build. Do not run git commit/push — the user owns version control."}}'
